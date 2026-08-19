from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Protocol

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types
from pydantic import BaseModel

from app.compiler.budget import (
    BudgetError,
    ModelPricing,
    ModelUsage,
    SQLiteBudgetLedger,
)
from app.compiler.models import DecisionDraft, DecisionProposal, ModelMetadata
from app.compiler.prompts import REASONER_SYSTEM_INSTRUCTION, reasoner_user_prompt
from app.compiler.reasoner_types import ReasoningRequest
from app.compiler.tools import ReadOnlySourceTools


class ReasonerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class StructuredOutputError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ModelInvocation:
    call_id: str
    model_name: str
    prompt_version: str
    system_instruction: str
    user_prompt: str
    output_schema: type[BaseModel]
    temperature: float
    tools: tuple[Callable[..., Any], ...] = ()


@dataclass(frozen=True, slots=True)
class StructuredModelResponse:
    parsed: BaseModel
    provider: str
    model_name: str
    model_version: str | None
    response_id: str | None
    execution_id: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int


class StructuredModelTransport(Protocol):
    def generate(self, invocation: ModelInvocation) -> StructuredModelResponse: ...


@dataclass(frozen=True, slots=True)
class AdkExecutionResult:
    raw_text: str
    response_id: str | None
    model_version: str | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


class AdkExecutor(Protocol):
    def execute(
        self,
        agent: Agent,
        prompt: str,
        *,
        user_id: str,
        session_id: str,
    ) -> AdkExecutionResult: ...


class DefaultAdkExecutor:
    def execute(
        self,
        agent: Agent,
        prompt: str,
        *,
        user_id: str,
        session_id: str,
    ) -> AdkExecutionResult:
        return asyncio.run(
            self._execute_async(
                agent,
                prompt,
                user_id=user_id,
                session_id=session_id,
            )
        )

    async def _execute_async(
        self,
        agent: Agent,
        prompt: str,
        *,
        user_id: str,
        session_id: str,
    ) -> AdkExecutionResult:
        events = await InMemoryRunner(agent=agent).run_debug(
            prompt,
            user_id=user_id,
            session_id=session_id,
            quiet=True,
        )
        raw_text = ""
        response_id: str | None = None
        model_version: str | None = None
        input_tokens = 0
        output_tokens = 0
        cached_input_tokens = 0
        for event in events:
            content = getattr(event, "content", None)
            if content is not None:
                candidate = "".join(
                    part.text or ""
                    for part in content.parts or []
                    if getattr(part, "text", None)
                )
                if candidate:
                    raw_text = candidate
            response_id = getattr(event, "id", None) or response_id
            model_version = getattr(event, "model_version", None) or model_version
            usage = getattr(event, "usage_metadata", None)
            if usage is not None:
                input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
                output_tokens = int(
                    getattr(usage, "candidates_token_count", 0) or 0
                )
                cached_input_tokens = int(
                    getattr(usage, "cached_content_token_count", 0) or 0
                )
        if not raw_text:
            raise ReasonerError(
                "MODEL_OUTPUT_MISSING",
                f"ADK agent {agent.name} returned no structured output",
            )
        return AdkExecutionResult(
            raw_text=raw_text,
            response_id=response_id,
            model_version=model_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
        )


class AdkGeminiTransport:
    def __init__(self, *, executor: AdkExecutor | None = None) -> None:
        self._executor = executor or DefaultAdkExecutor()

    def generate(self, invocation: ModelInvocation) -> StructuredModelResponse:
        if not _is_allowed_gemini_model(invocation.model_name):
            raise ReasonerError(
                "GEMINI_MODEL_NOT_ALLOWED",
                "semantic dependency compiler requires Gemini 3.5 or newer",
            )
        agent = Agent(
            name="semantic_dependency_reasoner",
            model=invocation.model_name,
            instruction=invocation.system_instruction,
            tools=list(invocation.tools),
            output_schema=invocation.output_schema,
            generate_content_config=genai_types.GenerateContentConfig(
                temperature=invocation.temperature,
            ),
            mode="single_turn",
        )
        result = self._executor.execute(
            agent,
            invocation.user_prompt,
            user_id=invocation.call_id,
            session_id=invocation.call_id,
        )
        try:
            parsed = invocation.output_schema.model_validate_json(result.raw_text)
        except Exception as error:
            raise StructuredOutputError(str(error)) from error
        return StructuredModelResponse(
            parsed=parsed,
            provider="GOOGLE",
            model_name=invocation.model_name,
            model_version=result.model_version,
            response_id=result.response_id,
            execution_id=invocation.call_id,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            output_tokens=result.output_tokens,
        )


class DependencyReasoner:
    def __init__(
        self,
        transport: StructuredModelTransport,
        *,
        model_name: str,
        prompt_version: str,
        temperature: float = 0.0,
    ) -> None:
        self._transport = transport
        self._model_name = model_name
        self._prompt_version = prompt_version
        self._temperature = temperature

    def propose(
        self,
        request: ReasoningRequest,
        tools: ReadOnlySourceTools,
    ) -> DecisionDraft:
        schema_feedback: str | None = None
        for attempt in (1, 2):
            invocation = ModelInvocation(
                call_id=f"{request.execution_id}:reasoner:{attempt}",
                model_name=self._model_name,
                prompt_version=self._prompt_version,
                system_instruction=REASONER_SYSTEM_INSTRUCTION,
                user_prompt=reasoner_user_prompt(
                    request,
                    tools,
                    schema_feedback=schema_feedback,
                ),
                output_schema=DecisionProposal,
                temperature=self._temperature,
                tools=tools.model_tool_functions(),
            )
            try:
                response = self._transport.generate(invocation)
            except StructuredOutputError as error:
                schema_feedback = str(error)
                if attempt == 2:
                    raise ReasonerError(
                        "MODEL_SCHEMA_INVALID",
                        f"structured output remained invalid after retry: {error}",
                    ) from error
                continue
            if not isinstance(response.parsed, DecisionProposal):
                schema_feedback = (
                    "provider returned an object that is not a DecisionProposal"
                )
                if attempt == 2:
                    raise ReasonerError("MODEL_SCHEMA_INVALID", schema_feedback)
                continue
            proposal = response.parsed
            if proposal.decision_type != request.decision_type:
                raise ReasonerError(
                    "MODEL_DECISION_TYPE_MISMATCH",
                    "model changed the request decision type",
                )
            return proposal.to_draft(
                request_id=request.request_id,
                model_metadata=ModelMetadata(
                    provider=response.provider,
                    model_name=response.model_name,
                    model_version=response.model_version,
                    prompt_version=self._prompt_version,
                    temperature=self._temperature,
                    execution_id=response.execution_id,
                    response_id=response.response_id,
                    input_tokens=response.input_tokens,
                    cached_input_tokens=response.cached_input_tokens,
                    output_tokens=response.output_tokens,
                ),
            )
        raise AssertionError("reasoner retry loop exhausted")


class OpenAIResponsesTransport:
    """OpenAI Responses structured-output adapter with a durable spend gate."""

    def __init__(
        self,
        *,
        client: Any,
        budget: SQLiteBudgetLedger,
        pricing: ModelPricing,
        max_input_tokens: int,
        max_output_tokens: int,
    ) -> None:
        if max_input_tokens <= 0 or max_output_tokens <= 0:
            raise ValueError("model token limits must be positive")
        self._client = client
        self._budget = budget
        self._pricing = pricing
        self._max_input_tokens = max_input_tokens
        self._max_output_tokens = max_output_tokens

    def generate(self, invocation: ModelInvocation) -> StructuredModelResponse:
        prompt_bytes = len(
            (invocation.system_instruction + invocation.user_prompt).encode("utf-8")
        )
        if prompt_bytes > self._max_input_tokens:
            raise ReasonerError(
                "MODEL_INPUT_LIMIT_EXCEEDED",
                "bounded prompt exceeds configured conservative input limit",
            )
        try:
            self._budget.reserve(
                invocation.call_id,
                pricing=self._pricing,
                maximum_usage=ModelUsage(
                    input_tokens=self._max_input_tokens,
                    output_tokens=self._max_output_tokens,
                ),
            )
        except BudgetError as error:
            raise ReasonerError(error.code, error.message) from error

        try:
            response = self._client.responses.parse(
                model=invocation.model_name,
                input=[
                    {"role": "system", "content": invocation.system_instruction},
                    {"role": "user", "content": invocation.user_prompt},
                ],
                text_format=invocation.output_schema,
                max_output_tokens=self._max_output_tokens,
                reasoning={"effort": "low"},
            )
        except Exception as error:
            self._budget.release(invocation.call_id)
            raise ReasonerError(
                "MODEL_TRANSPORT_ERROR",
                f"OpenAI Responses call failed: {type(error).__name__}",
            ) from error

        usage = _openai_usage(response)
        try:
            self._budget.settle(invocation.call_id, actual_usage=usage)
        except BudgetError as error:
            raise ReasonerError(error.code, error.message) from error

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise StructuredOutputError("OpenAI response contained no parsed output")
        if not isinstance(parsed, invocation.output_schema):
            try:
                parsed = invocation.output_schema.model_validate(parsed)
            except Exception as error:
                raise StructuredOutputError(str(error)) from error
        actual_model = getattr(response, "model", invocation.model_name)
        return StructuredModelResponse(
            parsed=parsed,
            provider="OPENAI",
            model_name=invocation.model_name,
            model_version=(
                actual_model if actual_model != invocation.model_name else None
            ),
            response_id=getattr(response, "id", None),
            execution_id=invocation.call_id,
            input_tokens=usage.input_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            output_tokens=usage.output_tokens,
        )


def openai_luna_pricing() -> ModelPricing:
    return ModelPricing(
        provider="OPENAI",
        model_name="gpt-5.6-luna",
        input_usd_per_million="0.20",
        cached_input_usd_per_million="0.02",
        output_usd_per_million="1.20",
        pricing_version="openai-2026-08-19",
    )


def _openai_usage(response: Any) -> ModelUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        raise ReasonerError(
            "MODEL_USAGE_MISSING",
            "OpenAI response did not include token usage for budget settlement",
        )
    details = getattr(usage, "input_tokens_details", None)
    return ModelUsage(
        input_tokens=int(getattr(usage, "input_tokens", 0)),
        cached_input_tokens=int(getattr(details, "cached_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0)),
    )


def _is_allowed_gemini_model(model_name: str) -> bool:
    match = re.match(r"^gemini-(\d+)\.(\d+)(?:-|$)", model_name)
    if match is None:
        return False
    major, minor = (int(part) for part in match.groups())
    return major > 3 or (major == 3 and minor >= 5)


__all__ = [
    "DependencyReasoner",
    "AdkExecutionResult",
    "AdkGeminiTransport",
    "ModelInvocation",
    "OpenAIResponsesTransport",
    "ReasonerError",
    "ReasoningRequest",
    "StructuredModelResponse",
    "StructuredOutputError",
]
