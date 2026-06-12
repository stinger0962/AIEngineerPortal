"""Tests for the ziwei TTS proxy endpoint (MiniMax reused, monkeypatched)."""
from __future__ import annotations

import app.api.v1.routes.ziwei as ziwei_routes
from app.core.config import get_settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_tts_503_when_no_key(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    r = client.post("/api/v1/ziwei/tts", json={"text": "你好"})
    assert r.status_code == 503


def test_tts_returns_mp3_and_strips_markdown(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "k", raising=False)
    monkeypatch.setattr(s, "minimax_group_id", "g", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    seen = {}
    def fake_tts(text, voice_id, api_key, group_id, model, api_base):
        seen["text"] = text
        seen["voice_id"] = voice_id
        return b"ID3fakemp3"
    monkeypatch.setattr(ziwei_routes, "_tts_bytes", fake_tts)
    r = client.post("/api/v1/ziwei/tts", json={"text": "你命宫**紫微**坐守"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == b"ID3fakemp3"
    assert "**" not in seen["text"] and "紫微" in seen["text"]
    assert seen["voice_id"] == "Chinese (Mandarin)_Radio_Host"


def test_tts_400_empty_text(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "k", raising=False)
    monkeypatch.setattr(s, "minimax_group_id", "g", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    r = client.post("/api/v1/ziwei/tts", json={"text": "   "})
    assert r.status_code == 400


def test_tts_502_on_minimax_error(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "k", raising=False)
    monkeypatch.setattr(s, "minimax_group_id", "g", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    def boom(*a, **k):
        raise ValueError("MiniMax TTS error 1004")
    monkeypatch.setattr(ziwei_routes, "_tts_bytes", boom)
    r = client.post("/api/v1/ziwei/tts", json={"text": "你好"})
    assert r.status_code == 502
