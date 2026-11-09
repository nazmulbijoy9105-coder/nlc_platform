"""Sentry filtering must preserve real errors while protecting request credentials."""
from app.core.sentry import sentry_before_send


def test_expected_legal_gate_http_exception_is_not_reported_as_application_error():
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPException",
                    "value": (
                        "503: Rescue plans are withheld until the underlying legal rules "
                        "receive independent counsel approval and the legal score is released."
                    ),
                }
            ]
        }
    }

    assert sentry_before_send(event, {}) is None


def test_unexpected_database_error_is_retained_and_sensitive_values_are_redacted():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer top.secret.token",
                "Cookie": "session=private",
                "Accept": "application/json",
            }
        },
        "exception": {
            "values": [
                {
                    "type": "MultipleResultsFound",
                    "value": "Multiple rows were found when one or none was required",
                    "stacktrace": {
                        "frames": [
                            {
                                "vars": {
                                    "scope": {
                                        "headers": [
                                            (b"authorization", b"Bearer nested.secret.token"),
                                            (b"accept", b"application/json"),
                                        ]
                                    }
                                }
                            }
                        ]
                    },
                }
            ]
        },
    }

    result = sentry_before_send(event, {})

    assert result is event
    assert result["request"]["headers"]["Authorization"] == "[Filtered]"
    assert result["request"]["headers"]["Cookie"] == "[Filtered]"
    assert result["request"]["headers"]["Accept"] == "application/json"
    nested_headers = result["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"]["scope"]["headers"]
    assert nested_headers[0][1] == "[Filtered]"
    assert nested_headers[1][1] == b"application/json"
    assert "top.secret.token" not in repr(result)
    assert "nested.secret.token" not in repr(result)


def test_unexpected_http_503_is_not_suppressed():
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPException",
                    "value": "503: Database temporarily unavailable",
                }
            ]
        }
    }

    assert sentry_before_send(event, {}) is event
