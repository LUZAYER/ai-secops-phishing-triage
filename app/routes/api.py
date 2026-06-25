import json
import threading
from fastapi import APIRouter, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
from app.services.pipeline import run_triage, run_single
from app.core.config import Config

router = APIRouter(prefix="/api")

# Simple global status flag
_triage_running = False


@router.get("/alerts", name="api_alerts")
async def api_alerts(request: Request):
    alerts = request.app.state.db.get_all_alerts()
    return JSONResponse(alerts)


@router.get("/alerts/{alert_id}", name="api_alert")
async def api_alert(request: Request, alert_id: str):
    alert = request.app.state.db.get_alert(alert_id)
    if not alert:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(alert)


@router.get("/stats", name="api_stats")
async def api_stats(request: Request):
    return JSONResponse(request.app.state.db.get_stats())


@router.post("/analyze", name="api_analyze")
async def api_analyze(request: Request, background_tasks: BackgroundTasks):
    global _triage_running
    if _triage_running:
        return JSONResponse({"status": "already_running"})
    
    form = await request.form()
    model = form.get("model", "qwen")
    
    _triage_running = True
    
    import uuid
    job_id = f"JOB-{uuid.uuid4().hex[:6].upper()}"
    db = request.app.state.db
    db.add_job(job_id, Config.DATA_FILE, "Default JSON")
    
    def _run():
        global _triage_running
        try:
            db.update_job_status(job_id, "PROCESSING")
            run_triage(db, job_id=job_id, model=model)
            job = db.get_job(job_id)
            if job and job.get("status") != "CANCELED":
                db.update_job_status(job_id, "COMPLETED")
        except Exception as e:
            db.update_job_status(job_id, f"FAILED: {str(e)}")
        finally:
            _triage_running = False
            
    background_tasks.add_task(_run)
    return JSONResponse({"status": "started", "job_id": job_id})


@router.post("/reanalyze/{alert_id}", name="api_reanalyze")
async def api_reanalyze(request: Request, alert_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_single, request.app.state.db, alert_id)
    return JSONResponse({"status": "queued", "alert_id": alert_id})


@router.post("/status/{alert_id}", name="api_status")
async def api_status(request: Request, alert_id: str):
    body = await request.json()
    status = body.get("status")
    request.app.state.db.update_status(alert_id, status)
    return JSONResponse({"status": "updated"})


@router.get("/triage/status", name="api_triage_status")
async def triage_status():
    return JSONResponse({"running": _triage_running})

@router.get("/logs", name="api_logs")
async def api_logs():
    from app.core.logger import global_logger
    from fastapi.responses import HTMLResponse
    logs = global_logger.get_logs()
    if not logs:
        return HTMLResponse("<div class='text-muted'>[Terminal initialized - Waiting for output...]</div>")
    html = "".join([f"<div>{l}</div>" for l in logs])
    return HTMLResponse(html)

def _setup_upload_dir():
    import os
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

@router.post("/upload", name="api_upload")
async def upload_alert(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    import os, uuid
    form = await request.form()
    model = form.get("model", "qwen")
    content = await file.read()
    
    upload_dir = _setup_upload_dir()
    job_id = f"JOB-{uuid.uuid4().hex[:6].upper()}"
    filename = f"{job_id}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, 'wb') as f:
        f.write(content)

    global _triage_running
    if _triage_running:
        return JSONResponse({"status": "error", "message": "Triage is already running."})
        
    _triage_running = True
    db = request.app.state.db
    db.add_job(job_id, filename, "File Upload")
    
    def _run_and_cleanup():
        global _triage_running
        try:
            db.update_job_status(job_id, "PROCESSING")
            run_triage(db, filepath=file_path, force=True, job_id=job_id, model=model)
            job = db.get_job(job_id)
            if job and job.get("status") != "CANCELED":
                db.update_job_status(job_id, "COMPLETED")
        except Exception as e:
            db.update_job_status(job_id, f"FAILED: {str(e)}")
        finally:
            _triage_running = False

    background_tasks.add_task(_run_and_cleanup)
    return JSONResponse({"status": "success", "message": "File uploaded and triage started."})


@router.post("/paste", name="api_paste")
async def paste_alert(request: Request, background_tasks: BackgroundTasks):
    import os, json, uuid
    from datetime import datetime
    
    body = await request.json()
    paste_type = body.get("type", "text")
    content = body.get("content", "")
    model = body.get("model", "qwen")
    
    if not content.strip():
        return JSONResponse({"status": "error", "message": "Content is empty"})
        
    try:
        if paste_type == "json":
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
        else:
            data = [{
                "alert_id": f"PST-{uuid.uuid4().hex[:6].upper()}",
                "reported_at": datetime.now().isoformat() + "Z",
                "reported_by": "manual-paste",
                "sender_email": "unknown@paste.local",
                "sender_display_name": "Pasted Text",
                "subject": "Manual Submission",
                "body_text": content,
                "urls": [],
                "attachments": [],
                "headers": {"spf": "unknown", "dkim": "unknown", "dmarc": "unknown"}
            }]
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Parse error: {str(e)}"})

    upload_dir = _setup_upload_dir()
    job_id = f"JOB-{uuid.uuid4().hex[:6].upper()}"
    filename = f"{job_id}_paste.json"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, 'w') as f:
        json.dump(data, f)

    global _triage_running
    if _triage_running:
        return JSONResponse({"status": "error", "message": "Triage is already running."})
        
    _triage_running = True
    db = request.app.state.db
    source_label = "JSON Paste" if paste_type == "json" else "Text Paste"
    db.add_job(job_id, filename, source_label)
    
    def _run_and_cleanup():
        global _triage_running
        try:
            db.update_job_status(job_id, "PROCESSING")
            run_triage(db, filepath=file_path, force=True, job_id=job_id, model=model)
            job = db.get_job(job_id)
            if job and job.get("status") != "CANCELED":
                db.update_job_status(job_id, "COMPLETED")
        except Exception as e:
            db.update_job_status(job_id, f"FAILED: {str(e)}")
        finally:
            _triage_running = False

    background_tasks.add_task(_run_and_cleanup)
    return JSONResponse({"status": "success", "message": "Pasted content queued for triage."})

@router.post("/jobs/{job_id}/cancel", name="api_cancel_job")
async def cancel_job(request: Request, job_id: str):
    db = request.app.state.db
    job = db.get_job(job_id)
    if job and job.get("status") in ("QUEUED", "PROCESSING"):
        db.update_job_status(job_id, "CANCELED")
        from app.core.logger import log
        log(f"[Triage] Received cancel request for job {job_id}")
    return JSONResponse({"status": "canceled"})

@router.delete("/jobs/{job_id}", name="api_delete_job")
async def delete_job(request: Request, job_id: str):
    db = request.app.state.db
    db.update_job_status(job_id, "CANCELED") # mark as canceled if running
    db.delete_job(job_id)
    return JSONResponse({"status": "deleted"})
