import re

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_receipt_machine_is_served_at_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "SIDEQUEST" in response.text
    assert 'id="quest-form"' in response.text
    assert "⚡ Doomscroll escape" in response.text
    assert "15-min emergency quest" in response.text
    assert '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">' in response.text


def test_frontend_static_assets_are_served() -> None:
    stylesheet_response = client.get("/static/styles.css")
    script_response = client.get("/static/app.js")
    api_script_response = client.get("/static/api-client.js")
    receipt_script_response = client.get("/static/receipt-ui.js")
    progress_script_response = client.get("/static/progress-ui.js")
    progress_core_response = client.get("/static/progress-core.mjs")
    favicon_response = client.get("/static/favicon.svg")
    fallback_favicon_response = client.get("/favicon.ico")

    assert stylesheet_response.status_code == 200
    assert stylesheet_response.headers["content-type"].startswith("text/css")
    assert script_response.status_code == 200
    assert "javascript" in script_response.headers["content-type"]
    assert 'type="module" src="/static/app.js"' in client.get("/").text
    assert "localStorage" not in script_response.text
    assert api_script_response.status_code == 200
    assert "/api/progress" in api_script_response.text
    assert "/complete" in api_script_response.text
    assert receipt_script_response.status_code == 200
    assert progress_script_response.status_code == 200
    assert progress_core_response.status_code == 200
    assert favicon_response.status_code == 200
    assert favicon_response.headers["content-type"].startswith("image/svg+xml")
    assert fallback_favicon_response.status_code == 200
    assert fallback_favicon_response.headers["content-type"].startswith("image/svg+xml")


def test_frontend_module_imports_are_served() -> None:
    pending_paths = ["/static/app.js"]
    checked_paths: set[str] = set()

    while pending_paths:
        path = pending_paths.pop()
        if path in checked_paths:
            continue

        response = client.get(path)
        assert response.status_code == 200
        checked_paths.add(path)

        for relative_path in re.findall(r"from ['\"](\./[^'\"]+)['\"]", response.text):
            pending_paths.append(f"/static/{relative_path.removeprefix('./')}")

    assert checked_paths == {
        "/static/api-client.js",
        "/static/app.js",
        "/static/progress-core.mjs",
        "/static/progress-ui.js",
        "/static/receipt-ui.js",
        "/static/replacement-flow.mjs",
    }
