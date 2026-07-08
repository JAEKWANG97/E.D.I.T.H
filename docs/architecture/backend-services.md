---
id: architecture-backend-services
type: architecture
category: operations
applies_to:
  - SCG
  - user
  - developmentassistant
  - rag
risk:
  - operations
  - compatibility
---

# Architecture: Backend Services

## Service Boundaries

- `SCG` is the gateway layer and validates JWTs before routing protected
  requests.
- `user` owns user authentication, cookie token behavior, and user profile
  endpoints.
- `developmentassistant` receives GitLab webhooks, fetches MR data, calls RAG,
  posts review comments, and updates dashboard state.
- `rag/flaskProject` builds code/document evidence and asks the LLM for review
  findings.

## Review Implications

- Cross-service auth changes should be reviewed against both gateway and user
  service behavior.
- RAG response-shape changes must be reviewed against the Java client.
- Operational changes should preserve environment-based configuration and avoid
  logging secrets.
