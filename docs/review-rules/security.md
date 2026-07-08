---
id: security-review-rules
type: review-rule
category: security
applies_to:
  - EncryptionUtil
  - JwtUtil
  - SecurityConfig
  - GitLabApi
risk:
  - security
  - operations
---

# Security Review Rules

## Secrets and Credentials

- Secrets, JWTs, refresh tokens, VCS tokens, and decrypted credentials must not
  be logged.
- New configuration values that carry secrets should come from environment
  variables with safe local defaults only when the default is non-production.
- Encryption key changes must preserve the ability to read existing encrypted
  data or document a migration path.

## Trust Boundaries

- External webhook, GitLab, and RAG service inputs should be treated as
  untrusted.
- Errors from external services should not expose tokens or sensitive request
  bodies in logs or API responses.

## Review Focus

- Check whether the change expands access to a previously protected endpoint.
- Check whether sensitive data can leak through logs, exceptions, or generated
  review comments.
