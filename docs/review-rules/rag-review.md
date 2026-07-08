---
id: rag-review-rules
type: review-rule
category: rag-review
applies_to:
  - reviewer.py
  - document_rag.py
  - CodeReviewRequest
  - CodeReviewResponse
  - RagServiceClient
risk:
  - ai-output
  - compatibility
---

# RAG Review Rules

## Evidence Grounding

- Reviews should be based on retrieved evidence, not generic review checklists.
- Each finding should be traceable to changed code, related code, project rules,
  API contracts, or historical findings.
- Retrieved evidence should include source labels and the reason it was selected.

## Output Compatibility

- The current Java client expects `review`, `summary`, and `techStacks`.
- LLM JSON output must be parsed defensively because code fences and explanatory
  text are common failure modes.
- Fallback review output should remain parseable by the Java client.

## Review Focus

- Check whether prompt changes increase false positives by forcing every section
  to be filled.
- Check whether retrieval changes preserve the GraphCodeBERT code path while
  adding document evidence.
