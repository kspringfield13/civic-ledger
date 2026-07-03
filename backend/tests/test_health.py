from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "civic-ledger"


def test_risk_signals_carry_disclaimer():
    resp = client.get("/risk-signals")
    assert resp.status_code == 200
    for signal in resp.json():
        assert "not a determination" in signal["disclaimer"]
