# API Standards

## RESTful Design
- Use nouns for resource endpoints (e.g., `/api/users`, `/api/orders`)
- HTTP methods map to CRUD: GET (read), POST (create), PUT (replace), PATCH (update), DELETE
- Use plural nouns for collection endpoints
- Nest resources logically (e.g., `/api/users/{id}/orders`)

## Request/Response Format
- JSON as primary format (Content-Type: application/json)
- Consistent response envelope:
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed",
  "errors": []
}
```

## Versioning
- Version API via URL prefix: `/api/v1/`
- Breaking changes require new version
- Maintain backward compatibility within a version

## Pagination
- Use cursor-based pagination for large datasets
- Response includes `next_cursor` and `has_more`

## Error Responses
- Use appropriate HTTP status codes
- Consistent error format with error code and message
- Include validation details for 422 responses
