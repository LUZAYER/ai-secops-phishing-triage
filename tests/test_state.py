import os
import pytest
from src.services.state_manager import StateManager

@pytest.fixture
def state_db(tmp_path):
    db_path = os.path.join(tmp_path, "test_alerts.db")
    return StateManager(db_path=db_path)

def test_state_manager(state_db):
    assert not state_db.exists("TEST-123")
    
    state_db.insert("TEST-123", "Benign", "Low", 90)
    assert state_db.exists("TEST-123")
    
    record = state_db.get("TEST-123")
    assert record["alert_id"] == "TEST-123"
    assert record["classification"] == "Benign"
    assert record["status"] == "PROCESSED"
