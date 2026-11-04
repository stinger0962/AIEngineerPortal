"""Read-only public smoke checks. Fixed URLs, verified TLS, no redirects."""
import json
import socket
import ssl
import time
import urllib.error
import urllib.request

ORIGIN = 'https://portal.leipan.cc'
ATTEMPTS = 5
DELAY_SECONDS = 10
TIMEOUT_SECONDS = 10
MAX_BODY_BYTES = 65536
CATEGORIES = frozenset({'http_status', 'redirect_refused', 'content_type',
                       'health_body', 'frontend_body', 'tls_error',
                       'dns_error', 'timeout', 'connection_error', 'probe_error'})


class ProbeError(ValueError):
    def __init__(self, category, status=None):
        self.category = category if category in CATEGORIES else 'probe_error'
        self.status = status if type(status) is int and 100 <= status <= 599 else None


def classify(error):
    if isinstance(error, ProbeError):
        return error.category, error.status
    if isinstance(error, urllib.error.HTTPError):
        code = error.code if type(error.code) is int and 100 <= error.code <= 599 else None
        return ('redirect_refused' if code is not None and 300 <= code < 400 else 'http_status'), code
    cause = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(cause, ssl.SSLError):
        return 'tls_error', None
    if isinstance(cause, socket.gaierror):
        return 'dns_error', None
    if isinstance(cause, TimeoutError):
        return 'timeout', None
    if isinstance(cause, (ConnectionError, OSError)) or isinstance(error, urllib.error.URLError):
        return 'connection_error', None
    return 'probe_error', None


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(opener, path, kind):
    request = urllib.request.Request(ORIGIN + path, headers={'Accept': kind})
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ProbeError('http_status', response.status)
        if response.headers.get_content_type() != kind:
            raise ProbeError('content_type')
        body = response.read(MAX_BODY_BYTES + 1)
        if kind == 'application/json':
            try:
                valid = len(body) <= MAX_BODY_BYTES and json.loads(body) == {'status': 'ok'}
            except (ValueError, UnicodeError):
                valid = False
            if not valid:
                raise ProbeError('health_body')
        elif b'<html' not in body.lower() and b'<!doctype html' not in body.lower():
            raise ProbeError('frontend_body')


def main():
    # Default context verifies certificates and hostnames; no insecure fallback.
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirects())
    for attempt in range(ATTEMPTS):
        passed = True
        for endpoint, path, kind in (('health', '/health', 'application/json'),
                                     ('frontend', '/', 'text/html')):
            try:
                probe(opener, path, kind)
            except Exception as error:
                passed = False
                category, status = classify(error)
                # Only fixed labels and bounded numeric status, never exception text/body.
                print('Public probe failed endpoint=' + endpoint + ' category=' + category
                      + ('' if status is None else ' status=' + str(status)))
        if passed:
            print('Public smoke checks passed')
            return 0
        if attempt + 1 < ATTEMPTS:
            time.sleep(DELAY_SECONDS)
    print('Public smoke checks failed')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
