---
id: api-user-auth
type: api-contract
category: auth
applies_to:
  - UserController
  - CookieUtil
  - JwtUtil
risk:
  - security
  - client-contract
---

# API: User Auth

## Endpoints

- `POST /api/v1/users/sign-in` authenticates a user and writes authentication
  cookies.
- `POST /api/v1/users/token/refresh` refreshes authentication and must update
  the access-token cookie for browser clients.
- `POST /api/v1/users/logout` clears authentication cookies.
- `GET /api/v1/users/validate` reports whether the current cookie token is
  valid.

## Contract Rules

- Auth endpoints that rely on HttpOnly cookies must not require the frontend to
  read or manually set JWTs.
- Refresh responses must keep cookie behavior compatible with sign-in.
- Logout must clear cookies using matching path and security attributes.
