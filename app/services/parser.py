import json
from typing import List
from app.models.alert import EmailAlert

class Parser:
    def parse_file(self, filepath: str) -> List[EmailAlert]:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return [EmailAlert(**item) for item in data]

    def parse(self, report_dict: dict) -> EmailAlert:
        return EmailAlert(**report_dict)
