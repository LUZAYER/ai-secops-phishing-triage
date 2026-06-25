from pydantic import BaseModel
from typing import List, Optional

class Attachment(BaseModel):
    filename: str
    extension: str

class Headers(BaseModel):
    return_path: str
    spf: str
    dkim: str
    dmarc: str

class EmailAlert(BaseModel):
    alert_id: str
    reported_at: str
    reported_by: str
    sender_email: str
    sender_display_name: str
    subject: str
    body_text: str
    urls: List[str]
    attachments: List[Attachment]
    headers: Headers
