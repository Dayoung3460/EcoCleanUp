# Copilot Instructions for EcoCleanUp

This repository is a **Flask + PostgreSQL** web app for managing community cleanup events.

## Project context

- Roles: `volunteer`, `event leader`, `admin`
- Key areas:
  - authentication and role-based access
  - volunteer registration/profile
  - event browsing/registration
  - feedback and participation history
  - leader/admin dashboards
- Main app package: `ecoapp/`
- Templates: `ecoapp/templates/`
- Static assets: `ecoapp/static/`
- SQL scripts: `create_database.sql`, `populate_database.sql`

## Tech and style expectations

- Use Python 3 and Flask conventions.
- Keep logic clear and assignment-oriented.
- Prefer small, focused changes over broad rewrites.
- Preserve existing naming patterns and route structure.
- When touching DB-related code, keep SQL scripts and app logic consistent.

## Commit message rules

When suggesting commit messages, follow this format:

`<type>(<scope>): <subject>`

- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Common scopes for this project:
  - `auth`, `volunteer`, `event-leader`, `admin`, `profile`, `events`
  - `registration`, `feedback`, `dashboard`, `db`, `sql`, `api`
  - `templates`, `static`, `ui`, `deploy`
- Subject rules:
  - imperative mood (e.g., `add volunteer signup validation`)
  - lowercase start
  - no trailing period
  - ideally within 72 characters

Optional body/footer:
- Body: explain **what changed and why** (focus on why)
- Footer examples: `BREAKING CHANGE: ...`, `Refs: #issue-number`

## Practical guidance for Copilot responses

- Prefer answers and edits aligned with current assignment scope.
- Avoid introducing unnecessary frameworks or major architecture changes.
- If requirements are unclear, ask for clarification before large changes.
- For UI work, keep Bootstrap-based templates simple and consistent.