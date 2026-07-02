# Security Standards

## Authentication & Authorization
- Use OAuth 2.0 / OpenID Connect for authentication
- Implement RBAC (Role-Based Access Control)
- All endpoints require authentication unless public
- Use short-lived JWTs with refresh tokens
- Store passwords using bcrypt/argon2

## Data Protection
- Encrypt data in transit (TLS 1.2+)
- Encrypt sensitive data at rest (AES-256)
- Never hardcode secrets; use environment variables or vault
- Regular secret rotation

## Input Validation
- Validate and sanitize all user inputs
- Use parameterized queries to prevent SQL injection
- Implement rate limiting on API endpoints
- Set request size limits

## Headers & CORS
- Set secure HTTP headers (CSP, HSTS, X-Frame-Options, etc.)
- Restrict CORS to trusted origins only
- Disable server version disclosure

## Dependencies
- Regular dependency scanning for vulnerabilities
- Pin dependency versions (no floating ranges)
- Review licenses of all dependencies
