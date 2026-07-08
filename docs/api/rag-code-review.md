---
id: api-rag-code-review
type: api-contract
category: rag-review
applies_to:
  - /rag/code-review
  - CodeReviewRequest
  - CodeReviewResponse
  - RagServiceClient
risk:
  - compatibility
  - ai-output
---

# API: RAG Code Review

## Request

- `POST /rag/code-review` accepts GitLab URL, token, project id, branch, MR
  metadata, changed files, and optional MR IID.
- MR title, description, and IID are additive context fields. Existing callers
  should remain valid when these fields are absent.

## Response

- The response must keep `status`, `review`, `summary`, and `techStacks`.
- Structured `findings` are additive and should include severity, category,
  file, line, issue, suggestion, and evidence.
- HTML or Markdown review text should be derived from structured findings when
  possible, not treated as the only source of truth.
