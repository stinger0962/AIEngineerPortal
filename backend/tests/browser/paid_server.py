"""Loopback-only browser QA fixture. Never included in an application entrypoint.

Codes go to an owner-only temporary file, not an HTTP test endpoint or logs.
The runner deletes the file and database on exit; no external email is sent.
"""
import json
import os
import socket
from pathlib import Path

if os.environ.get("PAID_BROWSER_QA") != "isolated-local-only":
    raise RuntimeError("Browser fixture requires the isolated QA runner")

root = Path(os.environ["PAID_QA_DIR"])
if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
    raise RuntimeError("Browser QA requires an owner-only temporary directory")

# Override all sensitive integration settings, even if a local .env exists.
os.environ.update(APP_ENV="test", PAID_ACCOUNTS_ENABLED="true",
    PAID_SESSION_SECURE="false", PAID_EMAIL_PROVIDER="disabled",
    DATABASE_URL=f"sqlite:///{root / 'unused-portal.db'}",
    PAID_DATABASE_URL=f"sqlite:///{root / 'paid.db'}",
    CORS_ORIGINS="http://127.0.0.1:3002", STRIPE_SECRET_KEY="",
    STRIPE_TEST_ENABLED="false", ANTHROPIC_API_KEY="", OPENAI_API_KEY="",
    MINIMAX_API_KEY="", ZIWEI_CLAIM_CODE="", ZIWEI_AUTO_ADOPT="false")

# This process never initiates any network connection, including to mail or AI.
def no_outbound(*args, **kwargs):
    raise RuntimeError("Browser QA forbids backend outbound connections")
socket.socket.connect = no_outbound
socket.socket.connect_ex = no_outbound

from app.core.config import get_settings
get_settings.cache_clear()
from app.paid_main import create_app
from app.services import paid_accounts as auth


def capture(email, code):
    if not email.endswith("@example.test"):
        raise ValueError("Reserved test addresses required")
    with os.fdopen(os.open(root / "outbox.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "a") as stream:
        stream.write(json.dumps({"email": email, "code": code}) + "\n")


app = create_app()
app.dependency_overrides[auth.get_sender] = lambda: capture


@app.middleware("http")
async def identify_fixture(request, call_next):
    response = await call_next(request)
    response.headers["X-Paid-QA-Run"] = os.environ["PAID_QA_RUN"]
    return response
