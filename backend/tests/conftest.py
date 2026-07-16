"""Shared pytest fixtures.

Runs the OTP test suite against the real MongoDB Atlas cluster the app
already uses (`settings.MONGODB_URI` / `src.config`), but against a
dedicated `-test` suffixed database so it never touches real dev/prod
data (e.g. `lucidex-01` -> `lucidex-01-test`). This mirrors exactly what
`src.database.connect_database()` does at app startup, just pointed at
a different database name and scoped to the OTP module's document model.

Each test gets a clean `otp_codes` collection: it's emptied after every
test function, and the whole test database is dropped once the full
suite finishes.
"""

from __future__ import annotations

import pytest
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import settings
from src.otp.models import OtpCode

TEST_DB_NAME = f"{settings.MONGODB_DB_NAME}-test"


@pytest.fixture(autouse=True)
async def otp_test_database():
    """Connect, init Beanie, run the test, then wipe the otp_codes collection."""
    client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
    await init_beanie(database=client[TEST_DB_NAME], document_models=[OtpCode])

    yield

    await OtpCode.get_motor_collection().delete_many({})
    client.close()


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    """Drop the entire `-test` database once, after the whole suite finishes."""
    yield

    import asyncio

    async def _drop():
        client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
        await client.drop_database(TEST_DB_NAME)
        client.close()

    asyncio.run(_drop())

