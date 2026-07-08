---
id: architecture-rag-pipeline
type: architecture
category: rag-review
applies_to:
  - reviewer.py
  - embeddings.py
  - document_rag.py
  - review_memory.py
risk:
  - ai-output
  - regression
---

# Architecture: RAG Pipeline

## Flow

GitLab changes are converted into file-level review queries. The pipeline
embeds code chunks, classifies the change, retrieves project documents, reranks
related code, adds historical review findings, and builds an Evidence Pack for
the LLM.

## Evidence Sources

- Changed diff and surrounding changed-file context.
- GraphCodeBERT code retrieval with code metadata.
- Document RAG for review rules, API contracts, ADRs, and architecture docs.
- Review memory for previously generated findings.

## Review Implications

- Retrieval should route by change category instead of adding all context.
- Evidence items should carry source and reason so findings can cite them.
- Token budget should prefer directly relevant evidence over generic rules.
