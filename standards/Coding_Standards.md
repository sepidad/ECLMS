# Coding Standards

## Language & Framework
- Use the latest stable version of the language/framework
- Follow the official style guide for the primary language

## Code Style
- Indentation: 2 spaces (no tabs)
- Maximum line length: 120 characters
- Semicolons required (where applicable)
- Single quotes preferred over double quotes for strings
- Trailing commas in multiline objects and arrays

## Best Practices
- DRY (Don't Repeat Yourself) - extract reusable logic
- KISS (Keep It Simple, Stupid) - prefer simple solutions
- Single Responsibility Principle - each function/class does one thing
- Favor composition over inheritance
- Use early returns to reduce nesting
- Avoid magic numbers/strings; use named constants

## Imports
- Group imports: built-in → external → internal
- Sort alphabetically within groups
- Use absolute imports for cross-module references

## Linting & Formatting
- Use ESLint/Prettier (or language equivalent)
- All code must pass linting before committing
- Format on save enabled in IDE
