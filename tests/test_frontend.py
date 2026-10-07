from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_receipt_machine_is_served_at_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "SIDEQUEST" in response.text
    assert 'id="quest-form"' in response.text


def test_frontend_static_assets_are_served() -> None:
    stylesheet_response = client.get("/static/styles.css")
    script_response = client.get("/static/app.js")
    progress_script_response = client.get("/static/progress.js")

    assert stylesheet_response.status_code == 200
    assert stylesheet_response.headers["content-type"].startswith("text/css")
    assert script_response.status_code == 200
    assert "javascript" in script_response.headers["content-type"]
    assert progress_script_response.status_code == 200
    assert "javascript" in progress_script_response.headers["content-type"]
