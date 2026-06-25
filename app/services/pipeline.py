"""
Triage pipeline — runs in background thread to keep the web UI responsive.
"""
import json
from app.core.database import Database
from app.core.config import Config
from app.services.parser import Parser
from app.services.features import FeatureExtractor
from app.services.llm import LLMAnalyzer
from app.services.reporter import ReportGenerator
from app.core.logger import log


def run_triage(db: Database, filepath: str = None, force: bool = False, job_id: str = None, model: str = "qwen"):
    filepath = filepath or Config.DATA_FILE
    parser   = Parser()
    extractor= FeatureExtractor()
    llm      = LLMAnalyzer(model=model)
    reporter = ReportGenerator(template_dir=Config.TEMPLATE_DIR, output_dir=Config.REPORTS_DIR)

    alerts = parser.parse_file(filepath)
    log(f"[Triage] Found {len(alerts)} alerts.")

    for alert in alerts:
        if job_id:
            job = db.get_job(job_id)
            if not job or job.get("status") == "CANCELED":
                log(f"[Triage] Job {job_id} was canceled. Stopping.")
                break

        if not force and db.exists(alert.alert_id):
            log(f"[Triage] {alert.alert_id} already processed — skip.")
            continue

        log(f"[Triage] Processing {alert.alert_id}…")
        features = extractor.extract(alert)
        analysis, threat_score = llm.analyze(alert, features)

        raw = alert.model_dump()
        db.upsert_alert(raw, analysis, threat_score)
        db.log_action(alert.alert_id, "Analyzed by LLM")
        reporter.generate(raw, analysis)
        log(f"[Triage] {alert.alert_id} done — {analysis['classification']} / {analysis['severity']}")

    log("[Triage] Complete.")


def run_single(db: Database, alert_id: str, model: str = "qwen"):
    """Re-analyze a single alert by ID."""
    parser    = Parser()
    extractor = FeatureExtractor()
    llm       = LLMAnalyzer(model=model)
    reporter  = ReportGenerator(template_dir=Config.TEMPLATE_DIR, output_dir=Config.REPORTS_DIR)

    alerts = parser.parse_file(Config.DATA_FILE)
    for alert in alerts:
        if alert.alert_id == alert_id:
            features = extractor.extract(alert)
            analysis, threat_score = llm.analyze(alert, features)
            raw = alert.model_dump()
            db.upsert_alert(raw, analysis, threat_score)
            db.log_action(alert_id, "Re-analyzed by analyst")
            reporter.generate(raw, analysis)
            return analysis
    return None
