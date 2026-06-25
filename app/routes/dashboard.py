from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.core.constants import SEVERITY_COLOR, STATUS_COLOR

router = APIRouter()

@router.get("/", name="dashboard")
async def dashboard(request: Request):
    db    = request.app.state.db
    stats = db.get_stats()
    recent_alerts = db.get_all_alerts()[:5]
    for a in recent_alerts:
        a["severity_color"] = SEVERITY_COLOR.get(a.get("severity"), "secondary")
        a["status_color"]   = STATUS_COLOR.get(a.get("status"), "secondary")
    return request.app.state.templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_alerts": recent_alerts,
    })
