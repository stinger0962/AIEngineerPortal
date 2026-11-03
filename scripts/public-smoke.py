"""Read-only public smoke checks. Fixed URLs, verified TLS, no redirects."""
import json
import ssl
import time
import urllib.request

ORIGIN = 'https://portal.leipan.cc'
ATTEMPTS = 5
DELAY_SECONDS = 10
TIMEOUT_SECONDS = 10
MAX_BODY_BYTES = 65536


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(opener, path, kind):
    request = urllib.request.Request(ORIGIN + path, headers={'Accept': kind})
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError('unexpected status')
        if response.headers.get_content_type() != kind:
            raise ValueError('unexpected content type')
        body = response.read(MAX_BODY_BYTES + 1)
        if kind == 'application/json':
            if len(body) > MAX_BODY_BYTES or json.loads(body) != {'status': 'ok'}:
                raise ValueError('unexpected health response')
        elif b'<html' not in body.lower() and b'<!doctype html' not in body.lower():
            raise ValueError('unexpected frontend response')


def main():
    # Default context verifies certificates and hostnames; no insecure fallback.
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirects())
    for attempt in range(ATTEMPTS):
        try:
            probe(opener, '/health', 'application/json')
            probe(opener, '/', 'text/html')
        except Exception:
            # Response bodies and exception details must not enter CI logs.
            if attempt + 1 < ATTEMPTS:
                time.sleep(DELAY_SECONDS)
            continue
        print('Public smoke checks passed')
        return 0
    print('Public smoke checks failed')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
