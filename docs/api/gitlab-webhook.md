---
id: api-gitlab-webhook
type: api-contract
category: async
applies_to:
  - WebhookController
  - WebhookEvent
  - CodeReviewService
  - GitLabApi
risk:
  - operations
  - reliability
---

# API: GitLab Webhook

## Contract

- `POST /api/v1/webhook` receives GitLab merge request webhook payloads.
- The handler extracts project id, MR IID, title, description, and user context
  used by the code review pipeline.
- The pipeline fetches MR changes from GitLab before calling the RAG service.

## Review Rules

- Webhook payload fields are external input and should be handled defensively.
- Async processing should log failures without exposing tokens.
- GitLab comment posting should preserve a fallback MR-wide note when inline
  mapping is unavailable.
