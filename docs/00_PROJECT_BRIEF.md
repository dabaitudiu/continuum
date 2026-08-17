# 00 — Project Brief

## Name

**Continuum**

## Track

Fortified Enterprise Fleet — strongest emphasis on **Core Execution & State**.

## One-sentence pitch

Continuum is a mission-control runtime for long-lived enterprise agents that detects when the assumptions behind old AI decisions have become stale and selectively revalidates only the affected execution branches.

## Problem

Long-running enterprise work spans days or weeks. During that time:

- policies change;
- permissions change;
- source documents get revised;
- human approvals arrive late;
- workers restart;
- tools return uncertain results;
- side effects may already have happened.

Traditional persistence answers **"where did the process stop?"**. Continuum must answer **"is it still semantically safe to continue from there?"**

## Demo domain

Enterprise vendor onboarding with three specialized agents:

- Vendor Agent
- Security Agent
- Procurement Agent

A security policy update invalidates a previously approved security decision while the mission is waiting. Continuum marks the affected decision and downstream branch stale, preserves unrelated work, requests new evidence, wakes on the new document, revalidates, and completes the onboarding.

## Primary wow moment

Policy changes from v12 to v13. A visible Decision Graph immediately changes:

- Security Review: `STALE`
- Procurement Approval: `STALE`
- Vendor Activation: `BLOCKED`
- Financial Review: `VALID`

Only the affected branch reruns.

## Success definition

A judge should understand the thesis without narration within ~10 seconds of seeing the graph transition.
