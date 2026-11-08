"""Read-only preview check unit tests; no network, credentials or deployments."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check-paid-preview.py"
spec = importlib.util.spec_from_file_location("paid_preview_check", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def healthy(base, path):
    responses = {
        "/health": (200, {}, json.dumps({"status":"ok","product":"paid-features","payments":"test-only"}).encode()),
        "/": (200, {}, "紫微 灵签".encode()),
        "/api/v1/account/session": (200, {"Cache-Control":"no-store"}, json.dumps({"authenticated":False,"enabled":False,"account_id":None}).encode()),
        "/api/v1/ziwei/profiles": (503, {}, b""),
        "/api/v1/billing/balance": (503, {}, b""),
        "/projects": (404, {}, b""),
        "/api/v1/ziwei/claim": (404, {}, b""),
        "/openapi.json": (404, {}, b""),
    }
    return responses[path]


def test_preview_is_never_a_live_launch_approval():
    result = check.inspect_preview("http://127.0.0.1:3100", healthy)
    assert result["preview_ready"] and not result["launch_ready"]
    assert "explicit_deployment_authorization" in result["unverified_launch_requirements"]


@pytest.mark.parametrize("base", ["https://example.com", "http://example.com", "http://localhost.evil", "http://127.0.0.1@evil.test", "http://user:secret@localhost", "http://127.0.0.1/path", "http://127.0.0.1?secret=x", "http://127.0.0.1#x", "http://127.0.0.1:99999"])
def test_reject_nonlocal_or_embedded_data_without_network(base):
    with pytest.raises(ValueError):
        check.inspect_preview(base, lambda *args: pytest.fail("network call"))


@pytest.mark.parametrize("base", ["http://127.0.0.1:3100", "http://localhost:3100/", "http://[::1]:3100"])
def test_local_origins(base):
    assert check.inspect_preview(base, healthy)["preview_ready"]


@pytest.mark.parametrize("path", ["/health", "/", "/api/v1/account/session", "/api/v1/ziwei/profiles", "/api/v1/billing/balance", "/projects", "/api/v1/ziwei/claim", "/openapi.json"])
def test_every_failed_check_fails_closed(path):
    def request(base, target):
        if target == path:
            return 200 if path != "/health" else 500, {}, b"secret provider error"
        return healthy(base,target)
    result = check.inspect_preview("http://localhost", request)
    assert not result["preview_ready"] and not result["launch_ready"]
    assert "secret" not in json.dumps(result)


def test_network_failure_redacted_and_no_early_success():
    def request(*args):
        raise OSError("secret local state")
    result = check.inspect_preview("http://localhost", request)
    assert not any(result["checks"].values()) and "secret" not in json.dumps(result)


def test_redirect_handler_refuses_forwarding():
    assert check.NoRedirects().redirect_request(None,None,302,"",{},"https://external.example") is None
