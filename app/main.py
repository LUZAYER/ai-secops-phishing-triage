"""
FastAPI application entry-point.
Run with:  uvicorn app.main:app --reload --port 8000
"""
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from app.core.config import Config
from app.core.database import Database
from app.routes import dashboard, alerts, reports, api, processing


def make_templates(directory: str):
    """Create a Jinja2 Environment with tojson filter, wrapping it
    so routes can call `app.state.templates.TemplateResponse(name, ctx)`."""
    env = Environment(loader=FileSystemLoader(directory), autoescape=True)
    env.filters["tojson"] = lambda v: json.dumps(v)

    class _Templates:
        def TemplateResponse(self, name: str, context: dict, status_code: int = 200):
            tmpl = env.get_template(name)
            return HTMLResponse(tmpl.render(**context), status_code=status_code)

    return _Templates()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(Config.DATABASE_PATH)
    app.state.db = db
    app.state.templates = make_templates(Config.TEMPLATE_DIR)
    yield


app = FastAPI(
    title="AI SecOps Phishing Triage",
    description="SOC dashboard powered by Ollama qwen3:8b",
    version="2.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(dashboard.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(processing.router)
app.include_router(api.router)
