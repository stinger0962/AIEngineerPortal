"""Static local-package safety checks. Docker build/runtime smoke is separate."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def configuration():
    return yaml.safe_load((ROOT / "compose.paid-local.yml").read_text())


def test_preview_only_exposes_loopback_proxy_and_uses_internal_network():
    config = configuration()
    assert set(config["services"]) == {"backend", "frontend", "proxy"}
    assert config["services"]["proxy"]["ports"] == ["127.0.0.1:3100:8080"]
    assert config["networks"] == {"paid-local": {"internal": True}, "paid-edge": {}}
    for name, service in config["services"].items():
        assert service["networks"] == (["paid-local", "paid-edge"] if name == "proxy" else ["paid-local"])
        if name != "proxy":
            assert "ports" not in service
        assert service["read_only"] is True
        assert service["restart"] == "no"
        assert service["cap_drop"] == ["ALL"]
        assert "no-new-privileges:true" in service["security_opt"]
        assert "env_file" not in service
        assert "secrets" not in service
        assert "network_mode" not in service
    assert "${" not in (ROOT / "compose.paid-local.yml").read_text()


def test_preview_storage_is_disposable_and_cannot_mount_portal_data():
    config = configuration()
    assert "volumes" not in config
    backend = config["services"]["backend"]
    assert "volumes" not in backend
    assert any(value.startswith("/data:") and "uid=10001" in value for value in backend["tmpfs"])
    assert backend["environment"]["PAID_DATABASE_URL"] == "sqlite:////data/paid.db"
    assert backend["environment"]["DATABASE_URL"] != backend["environment"]["PAID_DATABASE_URL"]
    assert config["services"]["proxy"]["volumes"] == ["./infra/paid-local/nginx.conf:/etc/nginx/nginx.conf:ro"]


def test_preview_never_inherits_or_enables_provider_credentials():
    env = configuration()["services"]["backend"]["environment"]
    assert env["APP_ENV"] == "development"
    assert env["PAID_SESSION_SECURE"] == "false"
    assert env["PAID_EMAIL_PROVIDER"] == "disabled"
    for key in ("PAID_ACCOUNTS_ENABLED", "STRIPE_TEST_ENABLED", "ZIWEI_REQUIRE_CREDITS", "ZIWEI_AUTO_ADOPT"):
        assert env[key] == "false"
    for key in ("PAID_EMAIL_FROM", "PAID_EMAIL_RESEND_API_KEY", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
                "STRIPE_TEST_BASE_URL", "ZIWEI_CLAIM_CODE", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                "MINIMAX_API_KEY", "MINIMAX_GROUP_ID", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        assert env[key] == ""


def test_backend_image_is_nonroot_paid_entrypoint_and_has_narrow_context():
    dockerfile = (ROOT / "backend/Dockerfile.paid").read_text()
    assert '"app.paid_main:app"' in dockerfile and '"app.main:app"' not in dockerfile
    assert '"--no-proxy-headers"' in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "COPY ." not in dockerfile
    assert "COPY --chown=paid:paid app ./app" in dockerfile
    assert "HEALTHCHECK" in dockerfile and "paid-features" in dockerfile
    ignores = (ROOT / "backend/Dockerfile.paid.dockerignore").read_text().splitlines()
    assert "*" in ignores and "!app/**" in ignores and "!requirements.txt" in ignores
    assert "**/.env" in ignores and "**/.env.*" in ignores and "**/*.db" in ignores


def test_compose_uses_dedicated_images_and_same_origin_api():
    services = configuration()["services"]
    assert services["backend"]["build"] == {"context": "./backend", "dockerfile": "Dockerfile.paid"}
    assert services["frontend"]["build"]["dockerfile"] == "Dockerfile.paid"
    assert services["frontend"]["build"]["args"]["NEXT_PUBLIC_API_BASE_URL"] == "/api/v1"
    assert services["frontend"]["build"]["args"]["SITE_URL"] == "http://localhost:3100"
    assert services["proxy"]["depends_on"] == {"backend": {"condition": "service_healthy"},
                                               "frontend": {"condition": "service_healthy"}}
