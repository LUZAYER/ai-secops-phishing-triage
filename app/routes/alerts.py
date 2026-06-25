import json
from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from app.core.constants import SEVERITY_COLOR, STATUS_COLOR, SEVERITIES
from app.services.pipeline import run_single

router = APIRouter(prefix="/alerts")

def _enrich(alert: dict) -> dict:
    alert["severity_color"] = SEVERITY_COLOR.get(alert.get("severity"), "secondary")
    alert["status_color"]   = STATUS_COLOR.get(alert.get("status"), "secondary")
    try:
        alert["urls_list"] = json.loads(alert.get("urls") or "[]")
    except Exception:
        alert["urls_list"] = []
    try:
        alert["attachments_list"] = json.loads(alert.get("attachments") or "[]")
    except Exception:
        alert["attachments_list"] = []
    try:
        alert["tactics_list"] = json.loads(alert.get("social_engineering_tactics") or "[]")
    except Exception:
        alert["tactics_list"] = []
    return alert


@router.get("/", name="alerts")
async def alert_list(request: Request, severity: str = "", status: str = "", q: str = ""):
    db     = request.app.state.db
    alerts = db.get_all_alerts(
        severity_filter=severity or None,
        status_filter=status or None,
        search=q or None,
    )
    for a in alerts:
        _enrich(a)
    return request.app.state.templates.TemplateResponse("alerts.html", {
        "request":   request,
        "alerts":    alerts,
        "severities": SEVERITIES,
        "severity_filter": severity,
        "status_filter":   status,
        "search":          q,
    })


@router.get("/{alert_id}", name="alert_detail")
async def alert_detail(request: Request, alert_id: str):
    db    = request.app.state.db
    alert = db.get_alert(alert_id)
    if not alert:
        return request.app.state.templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    _enrich(alert)
    audit = db.get_audit_log(alert_id)
    notes = db.get_notes(alert_id)
    return request.app.state.templates.TemplateResponse("alert_detail.html", {
        "request": request,
        "alert":   alert,
        "audit":   audit,
        "notes":   notes,
    })


@router.post("/{alert_id}/status", name="update_status")
async def update_status(request: Request, alert_id: str, status: str = Form(...)):
    request.app.state.db.update_status(alert_id, status)
    return RedirectResponse(url=f"/alerts/{alert_id}", status_code=303)


@router.post("/{alert_id}/note", name="add_note")
async def add_note(request: Request, alert_id: str, note: str = Form(...)):
    request.app.state.db.add_note(alert_id, note)
    return RedirectResponse(url=f"/alerts/{alert_id}", status_code=303)


@router.post("/{alert_id}/reanalyze", name="reanalyze")
async def reanalyze(request: Request, alert_id: str, background_tasks: BackgroundTasks):
    db = request.app.state.db
    background_tasks.add_task(run_single, db, alert_id)
    return RedirectResponse(url=f"/alerts/{alert_id}", status_code=303)
