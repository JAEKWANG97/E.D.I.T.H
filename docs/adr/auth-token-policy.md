---
id: adr-auth-token-policy
type: architecture-decision
category: auth
applies_to:
  - JwtUtil
  - CookieUtil
  - JwtCookieAuthenticationFilter
  - UserController
risk:
  - security
  - compatibility
---

# ADR: Auth Token Policy

## Decision

- Browser authentication uses HttpOnly cookies for the access token.
- Refresh-token flows must issue a new access token and write it back through
  the same cookie mechanism used by sign-in.
- Gateway and user-service JWT validation must agree on token signing, expiry,
  and claim interpretation.

## Review Implications

- Changes to `/token/refresh`, `CookieUtil`, or JWT utilities are high-risk.
- Reviewers should check whether browser clients can continue authentication
  without reading or writing tokens directly in JavaScript.
- Any change to cookie flags must preserve production-safe defaults for
  `HttpOnly`, `Secure`, and `SameSite` behavior.
