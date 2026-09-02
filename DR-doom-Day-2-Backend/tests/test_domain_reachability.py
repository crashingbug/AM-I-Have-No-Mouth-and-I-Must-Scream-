from fastapi.testclient import TestClient
import requests

from app.main import app
from app.services.domain_reachability import (
    compile_verification_list,
    ping_url,
    resolve_reachable_domain,
)

client = TestClient(app)


def test_compile_verification_list_registry() -> None:
    candidates = compile_verification_list("xhamster.com")
    assert "https://xhamster.com" in candidates
    assert "https://xhamster1.com" in candidates
    assert len(candidates) >= 2


def test_compile_verification_list_custom() -> None:
    custom = ["https://mirror1.org", "https://mirror2.org"]
    candidates = compile_verification_list("example.org", custom_mirrors=custom)
    assert candidates == custom


def test_resolve_reachable_domain_primary_success(monkeypatch) -> None:
    def fake_ping(url: str, timeout: float = 3.0):
        if url == "https://xhamster.com":
            return True, 200, None
        return False, 500, "Server Error"

    monkeypatch.setattr("app.services.domain_reachability.ping_url", fake_ping)

    result = resolve_reachable_domain("xhamster.com")
    assert result["active"] is True
    assert result["verified_url"] == "https://xhamster.com"
    assert len(result["checked_mirrors"]) == 1
    assert "Operational URL verified: https://xhamster.com" in result["message"]


def test_resolve_reachable_domain_fallback_on_error(monkeypatch) -> None:
    checked: list[str] = []

    def fake_ping(url: str, timeout: float = 3.0):
        checked.append(url)
        if url == "https://xhamster.com":
            return False, 403, "HTTP status 403"
        if url == "https://xhamster1.com":
            return False, None, "Connection timeout"
        if url == "https://xhamster1.desi":
            return True, 200, None
        return False, 404, "HTTP status 404"

    monkeypatch.setattr("app.services.domain_reachability.ping_url", fake_ping)

    result = resolve_reachable_domain("xhamster.com")
    assert result["active"] is True
    assert result["verified_url"] == "https://xhamster1.desi"
    assert len(result["checked_mirrors"]) == 3
    assert result["checked_mirrors"][0]["success"] is False
    assert result["checked_mirrors"][0]["status_code"] == 403
    assert result["checked_mirrors"][1]["success"] is False
    assert result["checked_mirrors"][1]["error"] == "Connection timeout"
    assert result["checked_mirrors"][2]["success"] is True
    assert result["checked_mirrors"][2]["status_code"] == 200


def test_resolve_reachable_domain_all_mirrors_fail(monkeypatch) -> None:
    def fake_ping(url: str, timeout: float = 3.0):
        return False, 503, "HTTP status 503"

    monkeypatch.setattr("app.services.domain_reachability.ping_url", fake_ping)

    result = resolve_reachable_domain("xhamster.com")
    assert result["active"] is False
    assert result["verified_url"] is None
    assert result["message"] == "Error: All requested domain mirrors are currently unreachable."


def test_reachability_api_endpoint(monkeypatch) -> None:
    def fake_ping(url: str, timeout: float = 3.0):
        if "mirror2" in url:
            return True, 200, None
        return False, 404, "HTTP status 404"

    monkeypatch.setattr("app.services.domain_reachability.ping_url", fake_ping)

    response = client.post(
        "/api/reachability/check",
        json={
            "target": "custom-site.com",
            "mirrors": ["https://mirror1.com", "https://mirror2.com"],
            "timeoutSeconds": 2.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["target"] == "custom-site.com"
    assert data["active"] is True
    assert data["verifiedUrl"] == "https://mirror2.com"
    assert len(data["checkedMirrors"]) == 2
    assert data["checkedMirrors"][0]["success"] is False
    assert data["checkedMirrors"][1]["success"] is True
