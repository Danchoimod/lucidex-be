import asyncio

from app.core.database import connect_database, disconnect_database


async def main() -> None:
    """Initialize Beanie and create every index declared by document models."""
    await connect_database()
    await disconnect_database()


if __name__ == "__main__":
    asyncio.run(main())
