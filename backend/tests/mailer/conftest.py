import pytest


@pytest.fixture(autouse=True)
def otp_test_database():
    """Mailer unit tests do not require the OTP database fixture."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    """Avoid database cleanup because these tests never create database state."""
    yield
