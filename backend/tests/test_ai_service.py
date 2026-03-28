"""Tests for AIService exercise grading."""
import json
import pytest
from app.services.ai_service import AIService


@pytest.fixture
def ai_service():
    return AIService(api_key="test-key", model="claude-sonnet-4-20250514")


@pytest.fixture
def sample_exercise():
    return {
        "id": 1,
        "title": "Build a tool registry",
        "prompt_md": "Create a registry that validates tool schemas.",
        "solution_code": "def register_tool(schema): ...",
        "explanation_md": "The registry validates JSON schemas...",
    }


class TestBuildGradingPrompt:
    def test_builds_system_prompt(self, ai_service, sample_exercise):
        prompt = ai_service._build_grading_prompt(
            code="def register_tool(): pass",
            exercise=sample_exercise,
            attempts_history=[],
        )
        assert "full-stack engineer" in prompt["system"]
        assert "Build a tool registry" in prompt["user"]
        assert "def register_tool(): pass" in prompt["user"]

    def test_includes_attempt_history(self, ai_service, sample_exercise):
        history = [{"code": "v1", "score": 45}]
        prompt = ai_service._build_grading_prompt(
            code="def register_tool(): pass",
            exercise=sample_exercise,
            attempts_history=history,
        )
        assert "previous attempt" in prompt["user"].lower()

    def test_limits_history_to_3(self, ai_service, sample_exercise):
        history = [{"code": f"v{i}", "score": i * 10} for i in range(10)]
        prompt = ai_service._build_grading_prompt(
            code="final", exercise=sample_exercise, attempts_history=history,
        )
        assert "v9" in prompt["user"]


class TestParseGradingResponse:
    def test_parses_valid_json(self, ai_service):
        raw = json.dumps({
            "strengths": ["Good structure"],
            "issues": ["Missing validation"],
            "suggestions": ["Add type checks"],
            "example_fixes": "```python\ndef validate(): ...\n```",
            "score": 72,
            "should_retry": True,
        })
        result = ai_service._parse_grading_response(raw)
        assert result["score"] == 72
        assert result["should_retry"] is True
        assert len(result["strengths"]) == 1

    def test_handles_markdown_wrapped_json(self, ai_service):
        raw = '```json\n{"strengths": [], "issues": [], "suggestions": [], "example_fixes": "", "score": 50, "should_retry": true}\n```'
        result = ai_service._parse_grading_response(raw)
        assert result["score"] == 50

    def test_handles_malformed_json(self, ai_service):
        result = ai_service._parse_grading_response("not json at all")
        assert result["score"] == 0
        assert result["should_retry"] is True
        assert len(result["issues"]) > 0


class TestCacheKey:
    def test_different_exercises_different_keys(self, ai_service):
        k1 = ai_service.cache_key(1, "code")
        k2 = ai_service.cache_key(2, "code")
        assert k1 != k2

    def test_different_code_different_keys(self, ai_service):
        k1 = ai_service.cache_key(1, "code_a")
        k2 = ai_service.cache_key(1, "code_b")
        assert k1 != k2

    def test_same_input_same_key(self, ai_service):
        k1 = ai_service.cache_key(1, "same")
        k2 = ai_service.cache_key(1, "same")
        assert k1 == k2


class TestIsAvailable:
    def test_available_with_key(self):
        svc = AIService(api_key="real-key")
        assert svc.is_available is True

    def test_unavailable_without_key(self):
        svc = AIService(api_key="")
        assert svc.is_available is False
