from fastapi import APIRouter, Request

router = APIRouter(prefix="/processing", tags=["processing"])

@router.get("/", name="processing")
async def processing_list(request: Request):
    db = request.app.state.db
    jobs = db.get_jobs()
    
    return request.app.state.templates.TemplateResponse("processing.html", {
        "request": request,
        "jobs": jobs
    })
