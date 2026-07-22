import json
import logging

from src.logging import JsonFormatter


def test_json_formatter_keeps_safe_error_context_and_drops_secrets():
    record = logging.LogRecord(
        name="lucidex.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="admin_authentication_rejected",
        args=(),
        exc_info=None,
    )
    record.error_code = "INVALID_ADMIN_TOKEN"
    record.failure_reason = "invalid_or_expired_token"
    record.actor_role = "operations_admin"
    record.access_token = "secret-access-token"
    record.otp_code = "123456"
    record.password = "secret-password"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["error_code"] == "INVALID_ADMIN_TOKEN"
    assert payload["failure_reason"] == "invalid_or_expired_token"
    assert payload["actor_role"] == "operations_admin"
    serialized = json.dumps(payload)
    assert "secret-access-token" not in serialized
    assert "123456" not in serialized
    assert "secret-password" not in serialized
