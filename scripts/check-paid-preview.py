#!/usr/bin/env python3
"""Read-only loopback preview checks. Never certifies or activates a live launch."""
import argparse
import json
import urllib.error
import urllib.parse
import urllib.request

UNVERIFIED = [
    "final_domain_and_brand", "production_https_and_secure_session",
    "dedicated_production_database_and_backup_restore",
    "authorized_sender_and_real_mailbox_delivery", "trusted_proxy_rate_limits",
    "auth_retention_schedule", "payment_eligibility_pricing_and_refund_policy",
    "payment_webhooks_and_reconciliation", "explicit_deployment_authorization",
]


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_base(base):
    url = urllib.parse.urlsplit(base)
    if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
            or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
        raise ValueError("Only a loopback HTTP preview origin is allowed")
    # Trigger malformed-port validation without printing the supplied URL.
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError("Invalid preview port")
    return base.rstrip("/")


def fetch(base, path):
    request = urllib.request.Request(base + path, headers={"X-Paid-Client": "1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects())
    try:
        response = opener.open(request, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read(1_000_000)


def inspect_preview(base, request=fetch):
    base = validate_base(base)
    checks = {}
    def check(name, path, expected, predicate=lambda headers, body: True):
        try:
            status, headers, body = request(base, path)
            checks[name] = status == expected and bool(predicate(headers, body))
        except Exception:
            # No raw body, exception, input URL, credential or configuration output.
            checks[name] = False
    check("paid_api_health", "/health", 200,
          lambda h,b: json.loads(b) == {"status":"ok", "product":"paid-features", "payments":"test-only"})
    check("door_homepage", "/", 200, lambda h,b: "紫微" in b.decode() and "灵签" in b.decode())
    check("fresh_accounts_disabled", "/api/v1/account/session", 200,
          lambda h,b: json.loads(b) == {"authenticated":False,"enabled":False,"account_id":None}
          and h.get("Cache-Control") == "no-store")
    check("private_profiles_closed", "/api/v1/ziwei/profiles", 503)
    check("private_billing_closed", "/api/v1/billing/balance", 503)
    check("personal_portal_route_absent", "/projects", 404)
    check("legacy_claim_absent", "/api/v1/ziwei/claim", 404)
    check("backend_schema_not_public", "/openapi.json", 404)
    return {"preview_ready": all(checks.values()), "checks": checks,
            "launch_ready": False, "unverified_launch_requirements": UNVERIFIED}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:3100")
    args = parser.parse_args()
    try:
        report = inspect_preview(args.base)
    except ValueError:
        print(json.dumps({"preview_ready":False, "launch_ready":False, "error":"Invalid local preview origin"}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["preview_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
