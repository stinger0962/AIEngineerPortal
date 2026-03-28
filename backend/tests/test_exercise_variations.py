"""Tests for exercise variation generation."""
import json
import pytest
from app.services.ai_service import AIService


@pytest.fixture
def ai_service():
    return AIService(api_key="test-key", model="claude-sonnet-4-20250514")


@pytest.fixture
def seed_exercise():
    return {
        "id": 1,
        "title": "Build a tool registry",
        "category": "agents",
        "difficulty": "intermediate",
        "prompt_md": "Create a registry that validates tool schemas.",
        "starter_code": "class ToolRegistry:\n    pass",
        "solution_code": "class ToolRegistry:\n    def register(self, tool): ...",
        "explanation_md": "The registry validates JSON schemas...",
    }


class TestBuildVariationPrompt:
    def test_scenario_prompt_mentions_different_domain(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "scenario")
        assert "different" in prompt["system"].lower()
        assert "Build a tool registry" in prompt["user"]

    def test_concept_prompt_mentions_different_pattern(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "concept")
        assert "different" in prompt["system"].lower()

    def test_harder_prompt_mentions_constraints(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "harder")
        assert "harder" in prompt["system"].lower() or "constraint" in prompt["system"].lower()

    def test_includes_seed_exercise_content(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "scenario")
        assert seed_exercise["prompt_md"] in prompt["user"]
        assert seed_exercise["solution_code"] in prompt["user"]


class TestParseVariationResponse:
    def test_parses_valid_json(self, ai_service):
        raw = json.dumps({
            "title": "Weather API tool registry",
            "prompt_md": "Build a registry for weather tools...",
            "starter_code": "class WeatherRegistry:\n    pass",
            "solution_code": "class WeatherRegistry:\n    def register(self): ...",
            "explanation_md": "The weather registry...",
        })
        result = ai_service._parse_variation_response(raw)
        assert result["title"] == "Weather API tool registry"
        assert "prompt_md" in result

    def test_handles_malformed_json(self, ai_service):
        result = ai_service._parse_variation_response("not json")
        assert result is None
