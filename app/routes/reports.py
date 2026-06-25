import os
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix="/reports")

@router.get("/", name="reports")
async def report_list(request: Request):
    reports_dir = "reports"
    files = []
    if os.path.exists(reports_dir):
        files = sorted([f for f in os.listdir(reports_dir) if f.endswith(".md")])
    return request.app.state.templates.TemplateResponse("reports.html", {
        "request": request,
        "reports": files,
    })

@router.get("/{filename}", name="report_detail")
async def report_view(request: Request, filename: str):
    filepath = os.path.join("reports", filename)
    if not os.path.exists(filepath):
        return request.app.state.templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    with open(filepath) as f:
        content = f.read()
    return request.app.state.templates.TemplateResponse("report_detail.html", {
        "request":  request,
        "filename": filename,
        "content":  content,
    })

@router.get("/{filename}/download", name="report_download")
async def report_download(filename: str):
    filepath = os.path.join("reports", filename)
    return FileResponse(filepath, media_type="text/markdown", filename=filename)
