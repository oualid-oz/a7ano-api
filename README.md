# Organization Management Platform

A production-ready, modular backend for managing organizations, teams, projects, memos, and a secure encrypted vault. Built with **FastAPI**, **SQLAlchemy 2.0 async**, **PostgreSQL**, **Redis**, and **Clean Architecture** / **Domain-Driven Design** principles.

## Features

- JWT authentication with refresh tokens, session management, device tracking, and account lockout.
- Role-based access control (RBAC) with permissions, roles, and scoped user roles.
- Organizations, teams, projects, memos, and a secure vault with AES-256-GCM encryption.
- Audit logging, rate limiting, CORS, secure headers, and structured logging.
- Async database operations, Alembic migrations, and comprehensive pytest coverage.
- Docker & Docker Compose for local development and deployment.
- GitHub Actions CI/CD with linting, formatting, type checking, and tests.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Project Structure](STRUCTURE.md)
- API docs (OpenAPI/Swagger) will be available at `/api/v1/docs` after startup.
