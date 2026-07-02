# Naming Convention Standards

## General Rules
- Use descriptive and meaningful names
- Avoid abbreviations unless widely accepted
- Use consistent casing throughout the codebase

## Casing Conventions
- **PascalCase**: Classes, interfaces, enums, methods, public properties
- **camelCase**: Local variables, method parameters, private fields
- **UPPER_SNAKE_CASE**: Constants, environment variables
- **kebab-case**: File names, directory names, URLs, CSS classes
- **snake_case**: Database columns, JSON keys, configuration files

## File & Directory Naming
- All lowercase with hyphens (kebab-case)
- Example: `user-profile.ts`, `api-client.ts`
- Test files: `*.test.ts` or `*.spec.ts`
- Component files: match the exported component name (PascalCase)

## Branch Naming
- `feature/description` - new features
- `fix/description` - bug fixes
- `hotfix/description` - urgent fixes
- `chore/description` - maintenance tasks
