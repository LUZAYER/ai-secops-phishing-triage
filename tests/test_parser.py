import pytest
from src.services.parser import Parser
from pydantic import ValidationError

def test_valid_record():
    parser = Parser()
    data = {
        "alert_id": "TEST-001",
        "reported_at": "2023-10-01T10:00:00Z",
        "reported_by": "user@test.com",
        "sender_email": "bad@evil.com",
        "sender_display_name": "Evil",
        "subject": "Test",
        "body_text": "Test",
        "urls": [],
        "attachments": [],
        "headers": {"return_path": "bad@evil.com", "spf": "fail", "dkim": "fail", "dmarc": "fail"}
    }
    alert = parser.parse(data)
    assert alert.alert_id == "TEST-001"
    assert alert.sender_email == "bad@evil.com"

def test_missing_field():
    parser = Parser()
    data = {
        "alert_id": "TEST-002"
    }
    with pytest.raises(ValidationError):
        parser.parse(data)
