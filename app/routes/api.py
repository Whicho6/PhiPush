from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.models.schemas import PlayerData
from app.services.phigros_cloud import CloudUnavailable, load_player
from app.services.push_planner import opportunities, target_route
from app.services.rks import build_best

router = APIRouter(prefix="/api")


class TokenBody(BaseModel):
    session_token: str = Field(min_length=10, max_length=256)


class AnalysisBody(BaseModel):
    target_rks: float | None = Field(default=None, ge=0, le=20)
    limit: int = Field(default=10, ge=1, le=30)


def _services(request: Request):
    return request.app.state


def _sid(x_phipush_session: str | None = Header(None), phipush_session: str | None = Cookie(None)) -> str | None:
    return x_phipush_session or phipush_session


def player(request: Request, sid: str | None = Depends(_sid)) -> PlayerData:
    found = request.app.state.sessions.get(sid)
    if not found:
        raise HTTPException(401, "PhiPush session missing or expired")
    return found


@router.get("/health")
def health(request: Request):
    return {"status": "ok" if not request.app.state.chart_data_error else "degraded",
            "mode": "mock" if request.app.state.mock else "real",
            "taptap_available": request.app.state.auth.available,
            "chart_data_available": not bool(request.app.state.chart_data_error),
            "chart_data_error": request.app.state.chart_data_error}


@router.post("/auth/mock")
def auth_mock(request: Request, response: Response):
    if not request.app.state.mock:
        raise HTTPException(404, "Mock mode is disabled")
    payload = json.loads(Path(request.app.state.mock_path).read_text(encoding="utf-8"))
    p = request.app.state.normalize(payload, request.app.state.charts)
    sid = request.app.state.sessions.create(p)
    response.set_cookie("phipush_session", sid, httponly=True, samesite="lax", max_age=request.app.state.sessions.ttl)
    return {"session_id": sid, "expires_in": request.app.state.sessions.ttl}


@router.post("/auth/session-token")
async def auth_token(body: TokenBody, request: Request, response: Response):
    if request.app.state.chart_data_error:
        raise HTTPException(503, request.app.state.chart_data_error)
    token = body.session_token
    try:
        p = await load_player(token, request.app.state.charts)
    except CloudUnavailable as exc:
        raise HTTPException(502, str(exc)) from None
    finally:
        token = ""  # drop the local reference as soon as the one read completes
        body.session_token = ""
    sid = request.app.state.sessions.create(p)
    response.set_cookie("phipush_session", sid, httponly=True, samesite="lax", max_age=request.app.state.sessions.ttl)
    return {"session_id": sid, "expires_in": request.app.state.sessions.ttl}


@router.post("/auth/taptap/start")
async def taptap_start(request: Request):
    if request.app.state.chart_data_error:
        raise HTTPException(503, request.app.state.chart_data_error)
    async def finish(session_token: str) -> str:
        try:
            loaded = await load_player(session_token, request.app.state.charts)
            return request.app.state.sessions.create(loaded)
        finally:
            session_token = ""
    try:
        attempt = await request.app.state.auth.start(finish)
    except Exception as exc:
        raise HTTPException(503, str(exc)) from None
    return {"login_id": attempt.login_id, "qr_url": attempt.qr_image, "verification_url": attempt.verification_url,
            "expires_in": max(0, int(attempt.expires_at - __import__('time').time()))}


@router.get("/auth/taptap/status/{login_id}")
def taptap_status(login_id: str, request: Request):
    attempt = request.app.state.auth.get(login_id)
    if not attempt:
        raise HTTPException(404, "Unknown login attempt")
    return {"status": attempt.status, "session_id": attempt.phipush_session, "error": attempt.error}


@router.get("/player/summary")
def summary(p: PlayerData = Depends(player)):
    best = build_best(p.records)
    return {"nickname": p.nickname, "current_rks": round(best.total, 6), "source_rks": p.source_rks,
            "record_count": len(p.records), "best_count": len(best.best) + len(best.phi), "b30_cutoff": round(best.cutoff, 6)}


@router.get("/player/records")
def records(p: PlayerData = Depends(player)):
    return {"records": [r.to_dict() for r in sorted(p.records, key=lambda x: x.chart_rks, reverse=True)]}


@router.get("/player/best")
def best(p: PlayerData = Depends(player)):
    result = build_best(p.records)
    slots = [(record, "phi", index) for index, record in enumerate(result.phi, 1)]
    slots += [(record, "best", index) for index, record in enumerate(result.best, 1)]
    ranked = []
    for index, (record, slot_type, slot_rank) in enumerate(sorted(slots, key=lambda item: item[0].chart_rks, reverse=True), 1):
        item = record.to_dict()
        item.update({"rank": index, "slot_type": slot_type, "slot_rank": slot_rank,
                     "total_rks_contribution": round(record.chart_rks / 30, 6)})
        ranked.append(item)
    return {"phi": [r.to_dict() for r in result.phi], "best": [r.to_dict() for r in result.best],
            "ranked": ranked, "current_rks": round(result.total, 6), "cutoff": round(result.cutoff, 6)}


@router.post("/analysis/opportunities")
def analyze(body: AnalysisBody, p: PlayerData = Depends(player)):
    return {"opportunities": [x.to_dict() for x in opportunities(p.records, body.limit)]}


@router.post("/analysis/target-route")
def route(body: AnalysisBody, p: PlayerData = Depends(player)):
    if body.target_rks is None:
        raise HTTPException(422, "target_rks is required")
    return target_route(p.records, body.target_rks)
