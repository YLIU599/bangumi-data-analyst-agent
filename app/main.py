from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes_agents import router as agent_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    base_dir = Path(__file__).resolve().parents[1]
    frontend_dir = base_dir / "frontend"
    templates = Jinja2Templates(directory=str(frontend_dir / "templates"))

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Bangumi Anime Reception Analyst.",
    )

    app.include_router(health_router)
    app.include_router(analysis_router, prefix=settings.api_prefix)
    app.include_router(agent_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)

    app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")

    outputs_dir = base_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

    @app.get("/", response_class=HTMLResponse, tags=["root"])
    async def root(request: Request):
        return templates.TemplateResponse(name="index.html", request=request)

    return app


app = create_app()
