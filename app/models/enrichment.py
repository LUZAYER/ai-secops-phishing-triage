from pydantic import BaseModel
from typing import List, Union

class EnrichmentResult(BaseModel):
    classification: str
    severity: str
    confidence: Union[int, float]
    social_engineering_tactics: List[str]
    rationale: str
    recommended_action: str
