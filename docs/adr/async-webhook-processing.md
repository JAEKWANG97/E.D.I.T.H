---
id: adr-async-webhook-processing
type: architecture-decision
category: async
applies_to:
  - WebhookController
  - CodeReviewService
  - AsyncConfig
  - GitLabApi
risk:
  - reliability
  - operations
---

# ADR: Async Webhook Processing

## Decision

- GitLab webhook receipt should stay lightweight.
- Long-running code review generation runs through `CodeReviewService` on the
  configured async executor.
- Failures inside review generation must be logged with project and MR context,
  while GitLab comment fallback behavior remains predictable.

## Review Implications

- Review changes touching webhook handling should check duplicate delivery,
  async exception handling, and executor saturation behavior.
- Posting comments and updating dashboard state should remain idempotent enough
  for repeated webhook events.
- Blocking network calls inside the webhook entrypoint should be avoided unless
  explicitly justified.
