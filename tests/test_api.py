from fastapi.testclient import TestClient

from app.main import create_app


def test_mock_api_end_to_end():
    with TestClient(create_app(mock=True)) as client:
        assert client.get("/api/health").json()["mode"] == "mock"
        auth = client.post("/api/auth/mock")
        assert auth.status_code == 200
        headers = {"X-PhiPush-Session": auth.json()["session_id"]}
        summary = client.get("/api/player/summary", headers=headers)
        assert summary.status_code == 200 and summary.json()["record_count"] >= 30
        best = client.get("/api/player/best", headers=headers)
        ranked = best.json()["ranked"]
        assert best.status_code == 200 and ranked
        assert ranked == sorted(ranked, key=lambda row: row["chart_rks"], reverse=True)
        assert all(row["slot_type"] in {"phi", "best"} for row in ranked)
        assert all(row["total_rks_contribution"] > 0 for row in ranked)
        assert all(row["slot_rank"] >= 1 for row in ranked)
        opps = client.post("/api/analysis/opportunities", json={}, headers=headers)
        assert opps.status_code == 200 and opps.json()["opportunities"]
        target = summary.json()["current_rks"] + .02
        route = client.post("/api/analysis/target-route", json={"target_rks": target}, headers=headers)
        assert route.status_code == 200 and route.json()["estimated_final_rks"] >= route.json()["current_rks"]


def test_real_mode_reports_missing_chart_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PHIPUSH_CHART_DATA", str(tmp_path / "missing.json"))
    with TestClient(create_app(mock=False)) as client:
        health = client.get("/api/health").json()
        assert health["status"] == "degraded"
        assert not health["chart_data_available"]
        response = client.post("/api/auth/session-token", json={"session_token": "not-a-real-token"})
        assert response.status_code == 503
        assert "完整曲库不可用" in response.json()["detail"]
