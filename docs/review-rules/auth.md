---
id: auth-review-rules
type: review-rule
category: auth
applies_to:
  - JwtUtil
  - CookieUtil
  - SecurityConfig
  - UserController
risk:
  - security
  - compatibility
---

# Auth Review Rules

## Token Lifecycle

- Access tokens and refresh tokens must not be interchangeable. If both are JWTs,
  the token payload should make the token purpose distinguishable.
- Refresh endpoints for HttpOnly cookie based authentication must update the
  `accessToken` cookie when they issue a new access token.
- Logout must clear both access and refresh cookies with the same path/security
  attributes used when the cookies were created.

## Cookie Safety

- `SameSite=None` cookies must be `Secure`.
- Authentication cookies should be `HttpOnly` unless a client-side token access
  requirement is explicitly documented.
- Do not log JWTs, refresh tokens, VCS tokens, or decrypted credentials.

## Review Focus

- Check whether the changed endpoint still works for browser clients that cannot
  directly write HttpOnly cookies.
- Check whether token expiration and refresh behavior remain consistent across
  gateway and service layers.
