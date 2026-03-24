from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze():
    payload = {"raw_text": "No water supply in Kakkanad"}
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert "structured_data" in data
    assert "scam_analysis" in data
    assert "cluster_info" in data
    assert data["report_available"] is True


def test_generate_report():
    analyze_data = client.post("/analyze", json={"raw_text": "OTP share cheyyan paranju"}).json()
    response = client.post(
        "/generate-report",
        json={"raw_text": "OTP share cheyyan paranju", "analysis": analyze_data},
    )
    assert response.status_code == 200
    body = response.json()
    assert "json_report" in body
    assert "markdown_report" in body
    assert "CivicSafe AI Report" in body["markdown_report"]
