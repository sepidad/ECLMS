# Logging Standards

## Log Levels
- **ERROR**: Application crashes, data corruption, unrecoverable errors
- **WARN**: Unexpected but recoverable issues, deprecated API usage
- **INFO**: Important business events, service lifecycle changes
- **DEBUG**: Detailed information for diagnosing problems (disabled in production)
- **TRACE**: Finest-grained logging for step-by-step tracing

## Log Format
Structured logging (JSON format):
```json
{
  "timestamp": "2024-01-01T00:00:00.000Z",
  "level": "INFO",
  "logger": "module.function",
  "message": "User created successfully",
  "context": { "userId": "123", "action": "create" },
  "traceId": "abc-123-def"
}
```

## Best Practices
- Include correlation/trace IDs for request tracking
- Never log sensitive data (passwords, tokens, PII)
- Log entry and exit for critical operations
- Use structured logging over string concatenation
- Configure log rotation and retention policies
- Centralized log aggregation (ELK, Datadog, etc.)
