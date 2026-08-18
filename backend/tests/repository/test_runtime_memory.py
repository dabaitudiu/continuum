from pathlib import Path

from app.repository.runtime_memory import InMemoryRuntimeRepository
from tests.repository.runtime_contract import RuntimeRepositoryContract


class TestInMemoryRuntimeRepository(RuntimeRepositoryContract):
    def make_repo(self, tmp_path: Path) -> InMemoryRuntimeRepository:
        return InMemoryRuntimeRepository()
