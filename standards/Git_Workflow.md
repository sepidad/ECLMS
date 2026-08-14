# Git Workflow Standards

## Branching Strategy
- **main**: Production-ready code (protected, no direct pushes)
- **develop**: Integration branch for features
- **feature/***: New feature development (branched from `develop`)
- **fix/***: Bug fixes (branched from `develop`)
- **hotfix/***: Urgent production fixes (branched from `main`)

## Commit Messages
Follow Conventional Commits specification:
```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `ci`, `build`

## Pull Requests
- PR title follows commit message format
- Description explains what and why
- Link to related issues
- At least one reviewer required
- Squash merge into target branch
- Delete branch after merge

## Code Review
- Review for logic, security, performance, and style
- Be constructive and specific
- Approve only when all concerns are addressed
