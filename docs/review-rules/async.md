---
id: async-review-rules
type: review-rule
category: async
applies_to:
  - Async
  - Executor
  - Webhook
  - CodeReviewService
risk:
  - reliability
  - operations
---

# Async Review Rules

## Webhook Processing

- Webhook handlers should return quickly and move long-running review work off
  the request thread.
- Exceptions in async work must be logged with enough context to identify the
  project and merge request.
- Validate that failures inside async processing do not leave callers assuming a
  review was posted successfully.

## Executor Safety

- Thread pool size and queue capacity should have explicit limits.
- Rejected or saturated work should have a visible failure mode or operational
  signal.

## Review Focus

- Check whether exceptions happen outside the intended `try` block.
- Check whether async work can duplicate comments or corrupt dashboard state
  when the same webhook is delivered multiple times.
