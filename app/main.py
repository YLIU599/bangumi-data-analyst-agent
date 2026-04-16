from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes_agents import router as agent_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend scaffold for the Bangumi Anime Reception Analyst.",
    )

    base_dir = Path(__file__).resolve().parent.parent
    frontend_static_dir = base_dir / "frontend" / "static"
    frontend_templates_dir = base_dir / "frontend" / "templates"
    outputs_dir = base_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=frontend_static_dir), name="static")
    app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

    templates = Jinja2Templates(directory=str(frontend_templates_dir))

    app.include_router(health_router)
    app.include_router(analysis_router, prefix=settings.api_prefix)
    app.include_router(agent_router, prefix=settings.api_prefix)

    @app.get("/", tags=["root"])
    async def root(request: Request):
        return templates.TemplateResponse(request, "index.html")

    return app


app = create_app()