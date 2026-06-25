import json
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.logger import log
from pydantic import ValidationError
from app.models.alert import EmailAlert
from app.models.enrichment import EnrichmentResult
from google import genai
from google.genai import types

SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {"type": "string"},
        "severity":       {"type": "string"},
        "confidence":     {"type": "number"},
        "social_engineering_tactics": {
            "type": "array",
            "items": {"type": "string"}
        },
        "rationale":          {"type": "string"},
        "recommended_action": {"type": "string"},
    },
    "required": [
        "classification", "severity", "confidence",
        "social_engineering_tactics", "rationale", "recommended_action"
    ]
}


class OllamaProvider:
    def __init__(self, model: str):
        self.model = model

    def analyze(self, prompt: str) -> dict:
        payload = {
            "model":   self.model,
            "messages": [{"role": "user", "content": prompt}],
            "format":   SCHEMA,
            "stream":   False,
            "options":  {"temperature": 0.0},
        }
        response = requests.post(
            "http://localhost:11434/api/chat", json=payload, timeout=600
        )
        response.raise_for_status()
        return json.loads(response.json()["message"]["content"])


class GeminiProvider:
    def __init__(self, model: str):
        self.model = model
        import os
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def analyze(self, prompt: str) -> dict:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SCHEMA,
                temperature=0.0,
            ),
        )
        return json.loads(response.text)


class LLMAnalyzer:
    def __init__(self, model: str = "qwen"):
        self.provider_choice = model
        self.fallback = OllamaProvider("llama3.1:8b")
        if model == "gemini":
            self.primary = GeminiProvider("gemini-2.5-pro")
        else:
            self.primary = OllamaProvider("qwen3:8b")

    # ── Deterministic threat scoring ─────────────────────────────────────────
    def calculate_threat_score(self, alert: EmailAlert, features: dict) -> int:
        score = 0
        if features.get("spf_fail"):  score += 10
        if features.get("dkim_fail"): score += 10
        if features.get("dmarc_fail"):score += 10
        if features.get("url_count", 0) > 0: score += 10
        text = (alert.body_text + " " + alert.subject).lower()
        if any(w in text for w in ["password", "credential", "login", "verify your identity"]):
            score += 30
        if ("urgent" in text or "rush" in text) and any(
            w in text for w in ["payment", "wire", "invoice", "gift card"]
        ):
            score += 30
        for att in alert.attachments:
            if att.extension.lower() in ["exe", "scr", "bat", "msi"]:
                score += 40
            elif att.extension.lower() in ["zip", "docm", "xlsm"]:
                score += 20
        return min(score, 100)

    def _det_severity(self, score: int) -> str:
        if score >= 70: return "Critical"
        if score >= 40: return "High"
        if score >= 20: return "Medium"
        return "Low"

    def _upgrade_severity(self, ai_sev: str, det_sev: str) -> str:
        levels = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        best   = max(levels.get(ai_sev, 1), levels.get(det_sev, 1))
        return {v: k for k, v in levels.items()}[best]

    # ── Main entry point ──────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def analyze(self, alert: EmailAlert, features: dict) -> tuple[dict, int]:
        """Returns (analysis_dict, threat_score)"""
        prompt = f"""You are a senior SOC phishing analyst.
Analyze the following phishing report.

EMAIL DATA
{alert.model_dump_json(indent=2)}

DERIVED SECURITY SIGNALS
{json.dumps(features, indent=2)}

TASKS
1. Classify email into exactly one of: Credential Phishing, Business Email Compromise, Malware Delivery, Spam, Benign, Unknown
2. Assign severity: Low, Medium, High, Critical
3. Identify social engineering tactics used
4. Provide detailed rationale
5. Recommend analyst action

Return ONLY valid JSON matching the provided schema. /no_think"""

        try:
            result = self.primary.analyze(prompt)
            if self.provider_choice == "gemini":
                log(f"  [gemini-2.5-pro] OK")
            else:
                log(f"  [qwen3:8b] OK")
        except Exception as e:
            log(f"  Primary failed: {e}. Trying fallback…")
            try:
                result = self.fallback.analyze(prompt)
                log(f"  [llama3.1:8b] OK")
            except Exception as e2:
                log(f"  Fallback failed: {e2}. Returning default.")
                result = {
                    "classification": "Unknown",
                    "severity": "Medium",
                    "confidence": 0,
                    "social_engineering_tactics": [],
                    "rationale": "Models unavailable.",
                    "recommended_action": "Manual review required.",
                }

        # Normalise confidence: model may return 0-1 float or 0-100 int
        raw_conf = result.get("confidence", 0)
        try:
            raw_conf = float(raw_conf)
            if raw_conf <= 1.0 and raw_conf > 0:
                raw_conf = int(raw_conf * 100)  # e.g. 0.85 -> 85
            else:
                raw_conf = int(raw_conf)         # e.g. 85 -> 85
        except (TypeError, ValueError):
            raw_conf = 0
        result["confidence"] = max(0, min(100, raw_conf))

        # Deterministic severity upgrade
        threat_score   = self.calculate_threat_score(alert, features)
        det_sev        = self._det_severity(threat_score)
        original_sev   = result.get("severity", "Low")
        final_sev      = self._upgrade_severity(original_sev, det_sev)
        result["severity"] = final_sev
        if original_sev != final_sev:
            result["rationale"] += (
                f" [Severity upgraded from {original_sev} to {final_sev} "
                f"by deterministic signal scoring (score={threat_score}).]"
            )

        # Pydantic validation
        try:
            validated = EnrichmentResult(**result)
            return validated.model_dump(), threat_score
        except ValidationError as e:
            log(f"  Validation error: {e}")
            return {
                "classification": "Unknown",
                "severity":       final_sev,
                "confidence":     0,
                "social_engineering_tactics": [],
                "rationale":          "LLM returned invalid schema.",
                "recommended_action": "Manual review required.",
            }, threat_score
