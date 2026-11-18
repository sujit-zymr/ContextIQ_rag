from app.observability import _sanitize_trace_value, redact_sensitive_text


def test_trace_content_is_redacted_by_default(monkeypatch):
    monkeypatch.delenv("LANGFUSE_CAPTURE_CONTENT", raising=False)

    value = _sanitize_trace_value({"question": "student private question", "sample_id": "Q01"})

    assert value == {"question": "[CONTENT REDACTED]", "sample_id": "Q01"}


def test_trace_content_can_be_enabled_but_secrets_remain_redacted(monkeypatch):
    monkeypatch.setenv("LANGFUSE_CAPTURE_CONTENT", "true")

    value = _sanitize_trace_value({"question": "attendance?", "api_key": "nvapi-1234567890abcd"})

    assert value["question"] == "attendance?"
    assert value["api_key"] == "[REDACTED_API_KEY]"


def test_passwords_and_tokens_are_always_redacted():
    value = _sanitize_trace_value({
        "password": "supersecretpassword",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        "nested": [{"access_token": "secret-token-xyz"}],
    })

    assert value["password"] == "[REDACTED]"
    assert value["authorization"] == "[REDACTED]"
    assert value["nested"][0]["access_token"] == "[REDACTED]"


def test_redact_sensitive_text_patterns():
    text = (
        "Authorization: Bearer mysecrettoken123456789 "
        "password=dbpass123 "
        "api_key: sk-proj-1234567890123456789012 "
        "contact: admin@college.edu "
        "URL: postgresql://user:dbpass@localhost:5432/ragdb"
    )
    redacted = redact_sensitive_text(text)

    assert "mysecrettoken123456789" not in redacted
    assert "dbpass123" not in redacted
    assert "sk-proj-1234567890123456789012" not in redacted
    assert "admin@college.edu" not in redacted
    assert "dbpass@" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED]" in redacted
