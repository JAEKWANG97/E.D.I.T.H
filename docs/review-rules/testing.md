---
id: testing-review-rules
type: review-rule
category: testing
applies_to:
  - test
  - Controller
  - Service
  - RAG
  - DTO
risk:
  - regression
---

# Testing Review Rules

## Required Regression Coverage

- Authentication changes should include coverage for cookie creation, refresh,
  logout, and unauthorized access behavior.
- API contract changes should include serialization or client compatibility
  checks when possible.
- RAG prompt or parser changes should include focused checks for output parsing
  and request/response compatibility.
- Async webhook changes should include at least one check that verifies failures
  are contained or logged.

## Review Focus

- Prefer behavior-focused tests over tests that only lock implementation detail.
- If full integration tests are expensive, require a small parser, DTO, or
  contract test that would fail on the most likely regression.
