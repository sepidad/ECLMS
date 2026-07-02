# Error Handling Standards

## Strategy
- Use a centralized error handling mechanism
- Never swallow exceptions silently
- Distinguish between expected (operational) and unexpected (programming) errors

## Error Types
- **Validation errors**: 400 - Invalid input from client
- **Authentication errors**: 401 - Missing/invalid credentials
- **Authorization errors**: 403 - Insufficient permissions
- **Not found errors**: 404 - Resource does not exist
- **Conflict errors**: 409 - Resource state conflict
- **Rate limit errors**: 429 - Too many requests
- **Internal errors**: 500 - Unexpected server failures

## Implementation
- Custom error classes with error codes and HTTP status
- Global error handler middleware (catch-all)
- Log all errors with stack traces (production-safe filtering)
- Return user-friendly messages (no internal details leaked)

## Async Error Handling
- Always handle promise rejections with `.catch()` or try/catch
- Use async error boundary wrappers
- Top-level unhandled rejection handler

## Client-Side
- Graceful degradation on API failures
- User-friendly error messages with retry options
- Boundary components for React/Vue to catch render errors
