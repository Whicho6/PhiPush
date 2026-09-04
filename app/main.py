from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.routes.api import router
from app.services.auth import TapTapAuth
from app.services.chart_data import ChartDataError, load_charts
from app.services.record_parser import normalize_player
from app.services.session_store import MemorySessions

ROOT = Path(__file__).resolve().parents[1]


def _load_chart_data(mock: bool) -> tuple[dict, str | None, Path]:
    configured = os.getenv("PHIPUSH_CHART_DATA")
    path = Path(configured).expanduser() if configured else ROOT / "data" / ("demo_charts.json" if mock else "charts.json")
    try:
        return load_charts(path), None, path
    except (OSError, ValueError, ChartDataError) as exc:
        message = (f"完整曲库不可用：{path}。请运行 scripts/update_chart_data.py 在本地生成，"
                   f"或设置 PHIPUSH_CHART_DATA。详情：{exc}")
        return {}, message, path


def create_app(mock: bool | None = None) -> FastAPI:
    mock = (os.getenv("PHIPUSH_MOCK") == "1") if mock is None else mock
    app = FastAPI(title="PhiPush API", version="0.1.0", docs_url="/api/docs", redoc_url=None)
    origins = [x.strip() for x in os.getenv("PHIPUSH_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-PhiPush-Session"])
    app.state.mock = mock
    app.state.mock_path = ROOT / "data" / "mock_player.json"
    app.state.charts, app.state.chart_data_error, app.state.chart_data_path = _load_chart_data(mock)
    app.state.normalize = normalize_player
    app.state.sessions = MemorySessions(int(os.getenv("PHIPUSH_SESSION_TTL", "900")))
    app.state.auth = TapTapAuth()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
    templates = Environment(loader=FileSystemLoader(ROOT / "app" / "templates"), autoescape=select_autoescape())

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.get_template("index.html").render(mock=app.state.mock, taptap=app.state.auth.available)

    return app


app = create_app()
