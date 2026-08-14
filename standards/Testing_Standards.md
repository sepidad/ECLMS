# Testing Standards

## Testing Pyramid
- **Unit tests**: 70% - Test individual functions/classes in isolation
- **Integration tests**: 20% - Test module interactions and API endpoints
- **E2E tests**: 10% - Test critical user workflows end-to-end

## Test Structure
- Follow AAA pattern: Arrange, Act, Assert
- Use descriptive test names that explain expected behavior
- One assertion (or assertion group) per test
- Tests should be independent and idempotent

## Coverage
- Minimum 80% code coverage target
- Cover branches, not just statements
- Critical paths require 100% coverage
- No coverage drop allowed on PRs

## Naming
- Test files: `*.test.ts` or `*.spec.ts` alongside source
- Test suites describe the unit under test
- Test names: `should [expected behavior] when [condition]`

## Best Practices
- Mock external dependencies (APIs, databases, filesystem)
- Use factories/fixtures for test data
- Avoid shared mutable state between tests
- Run tests in CI for every commit
- Clean up resources after tests
