import argparse
import asyncio

from app.core.application import create_app
from app.core.database import close_db, engine


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve")
    subparsers.add_parser("init-db")
    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn

        uvicorn.run(create_app(), host="0.0.0.0", port=8000)
    elif args.command == "init-db":
        asyncio.run(_init_db())


async def _init_db() -> None:
    from app.common.models import Base
    from app.models import (  # noqa: F401
        Organization,
        OrganizationInvitation,
        Permission,
        RefreshSession,
        Role,
        Team,
        User,
        UserRole,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await close_db()


if __name__ == "__main__":
    main()
