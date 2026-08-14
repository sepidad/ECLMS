# Database Standards

## Schema Design
- Use meaningful table and column names (snake_case)
- Plural table names (e.g., `users`, `orders`)
- Always include `id` (UUID or auto-increment) as primary key
- Include `created_at` and `updated_at` timestamp columns
- Use foreign keys for relationships

## Migrations
- All schema changes must be version-controlled as migrations
- Migrations must be reversible (up/down)
- One migration per logical change
- Never modify existing migrations after review

## Query Standards
- Use parameterized queries to prevent SQL injection
- Avoid N+1 queries; use eager loading
- Index columns used in WHERE, JOIN, and ORDER BY
- Use EXPLAIN ANALYZE to optimize slow queries
- Keep transactions short and focused

## Naming
- Tables: `snake_case`, plural (e.g., `user_roles`)
- Columns: `snake_case` (e.g., `first_name`)
- Indexes: `idx_table_column` (e.g., `idx_users_email`)
- Foreign keys: `fk_source_target` (e.g., `fk_orders_user_id`)
