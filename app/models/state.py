from pydantic import BaseModel
from typing import Optional

class AlertState(BaseModel):
    alert_id: str
    classification: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[int] = None
    status: str
    processed_at: str
