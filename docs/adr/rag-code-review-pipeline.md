---
id: adr-rag-code-review-pipeline
type: architecture-decision
category: rag-review
applies_to:
  - reviewer.py
  - document_rag.py
  - review_memory.py
  - CodeReviewResponse
risk:
  - ai-output
  - compatibility
---

# ADR: RAG Code Review Pipeline

## Decision

- Code retrieval keeps GraphCodeBERT for code chunks.
- Natural-language project documents use a separate text/document retrieval
  path instead of GraphCodeBERT.
- The reviewer prompt consumes an Evidence Pack rather than raw, unlabelled
  context.
- The canonical review output is structured findings JSON. HTML/Markdown review
  text is a rendered representation for current clients.

## Review Implications

- New findings should cite changed code, related code, project documents, or
  historical findings.
- RAG changes must preserve `review`, `summary`, and `techStacks` response
  compatibility for the Java client.
- Parser fallback behavior matters because LLM output can contain code fences or
  text around JSON.
