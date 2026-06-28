# Project Structure

Generated folder layout for the Organization Management Platform.

```
/home/oo/Workspace/a7ano.app
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── __init__.py
├── app/
│   ├── __init__.py
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── responses.py
│   │   ├── schemas.py
│   │   └── utils.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── application.py
│   │   ├── cache.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   ├── redis.py
│   │   └── security.py
│   ├── memos/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── organizations/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── permissions/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── projects/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── teams/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   ├── users/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tests/
│   └── vault/
│       ├── __init__.py
│       ├── dependencies.py
│       ├── encryption.py
│       ├── exceptions.py
│       ├── models.py
│       ├── repository.py
│       ├── router.py
│       ├── schemas.py
│       ├── service.py
│       └── tests/
├── scripts/
│   ├── bootstrap.sh
│   └── entrypoint.sh
├── tests/
│   ├── __init__.py
│   ├── app/
│   │   └── ...
│   ├── conftest.py
│   ├── factories.py
│   └── helpers.py
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── .pre-commit-config.yaml
├── ARCHITECTURE.md
├── Dockerfile
├── README.md
├── STRUCTURE.md
├── docker-compose.yml
└── pyproject.toml
```

Each module owns its domain, tests, and dependencies. The `app/core` package contains framework-level cross-cutting concerns only.
