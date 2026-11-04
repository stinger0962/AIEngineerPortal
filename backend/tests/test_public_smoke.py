"""Public smoke checks are fully mocked; no live site requests."""
import contextlib
from email.message import Message
import importlib.util
import io
from pathlib import Path
import ssl
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('smoke', ROOT / 'scripts/public-smoke.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SENTINEL = 'private-error-must-not-be-logged'


class Response:
    def __init__(self, body, kind, status=200):
        self.body, self.status = body, status
        self.headers = Message()
        self.headers['Content-Type'] = kind
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size):
        return self.body[:size]


class Opener:
    def __init__(self, error=None):
        self.calls = []
        self.requests = []
        self.error = error
    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        self.requests.append(request)
        if self.error:
            if isinstance(self.error, urllib.error.HTTPError):
                # Real requests return a new stream, never a previously closed error.
                raise urllib.error.HTTPError(self.error.url, self.error.code,
                                             self.error.msg, self.error.headers,
                                             io.BytesIO())
            raise self.error
        if request.full_url.endswith('/health'):
            return Response(b'{"status":"ok"}', 'application/json')
        return Response(b'<!doctype html><html></html>', 'text/html')


class PublicSmokeTests(unittest.TestCase):
    def test_http_denial_hints_are_allowlisted_and_body_reads_bounded(self):
        for status in (403, 302):
            streams = []
            def deny(request, timeout):
                headers = Message()
                headers['Server'] = 'cloudflare'
                headers['cf-ray'] = SENTINEL
                headers['cf-mitigated'] = 'challenge'
                headers['Set-Cookie'] = SENTINEL
                headers['Location'] = 'https://' + SENTINEL
                stream = io.BytesIO(b'/cdn-cgi/challenge-platform/ ' + SENTINEL.encode()
                                    + b'x' * MODULE.MAX_BODY_BYTES)
                stream.read = unittest.mock.Mock(wraps=stream.read)
                streams.append(stream)
                raise urllib.error.HTTPError(request.full_url, status, SENTINEL, headers, stream)
            with patch.object(Opener, 'open', side_effect=deny), \
                 patch.object(MODULE.urllib.request, 'getproxies', return_value={
                     'https': 'http://' + SENTINEL, 'no': SENTINEL}):
                code, _ = self.run_main(Opener())
            self.assertEqual(code, 1)
            self.assertIn('https_proxy_present=true no_proxy_present=true', self.output)
            self.assertIn('server_hint=cloudflare cf_challenge=true cf_marker=true', self.output)
            self.assertIn('body_hint=cloudflare_challenge', self.output)
            self.assertIn('status=' + str(status), self.output)
            for stream in streams:
                stream.read.assert_called_once_with(MODULE.MAX_BODY_BYTES + 1)
                self.assertTrue(stream.closed)

    def test_unknown_headers_and_body_never_reach_logs(self):
        response = Response(SENTINEL.encode(), 'text/html', 403)
        response.headers['Server'] = SENTINEL
        response.headers['cf-mitigated'] = SENTINEL
        response.read = unittest.mock.Mock(wraps=response.read)
        with patch.object(Opener, 'open', return_value=response):
            code, _ = self.run_main(Opener())
        self.assertEqual(code, 1)
        self.assertIn('server_hint=other_or_absent cf_challenge=false', self.output)
        self.assertIn('body_hint=unrecognized', self.output)
        self.assertEqual(response.read.call_count, 10)
        response.read.assert_called_with(MODULE.MAX_BODY_BYTES + 1)

    def test_error_body_read_failure_preserves_http_status_and_closes_stream(self):
        stream = io.BytesIO()
        stream.read = unittest.mock.Mock(side_effect=TimeoutError(SENTINEL))
        error = urllib.error.HTTPError(MODULE.ORIGIN, 403, SENTINEL, {}, stream)
        with patch.object(Opener, "open", side_effect=error):
            code, _ = self.run_main(Opener())
        self.assertEqual(code, 1)
        self.assertIn('category=http_status status=403', self.output)
        self.assertIn('body_hint=unavailable', self.output)
        self.assertTrue(stream.closed)

    def test_pr_diagnostic_has_only_read_permissions_and_no_production_actions(self):
        workflow = (ROOT / '.github/workflows/public-smoke-pr.yml').read_text()
        self.assertIn('pull_request:', workflow)
        self.assertIn('contents: read', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('timeout-minutes: 4', workflow)
        self.assertIn('python3 -B -m unittest discover', workflow)
        self.assertIn('python3 -B scripts/public-smoke.py', workflow)
        for forbidden in ('secrets.', 'ssh-action', 'deploy.yml', 'push:',
                          'packages:', 'write', 'pull_request_target:', 'continue-on-error'):
            self.assertNotIn(forbidden, workflow)

    def run_main(self, opener):
        output = io.StringIO()
        with patch.object(MODULE.urllib.request, 'build_opener', return_value=opener), \
             patch.object(MODULE.time, 'sleep') as sleep, contextlib.redirect_stdout(output):
            code = MODULE.main()
        self.assertNotIn(SENTINEL, output.getvalue())
        self.output = output.getvalue()
        return code, sleep

    def test_success_checks_only_fixed_https_urls_with_timeout(self):
        opener = Opener()
        code, sleep = self.run_main(opener)
        self.assertEqual(code, 0)
        self.assertEqual(opener.calls, [
            ('https://portal.leipan.cc/health', 10),
            ('https://portal.leipan.cc/', 10)])
        sleep.assert_not_called()

    def test_fixed_honest_application_identity_on_both_endpoints_and_retries(self):
        for error in (None, urllib.error.HTTPError(MODULE.ORIGIN, 403, SENTINEL, {}, None)):
            opener = Opener(error)
            code, _ = self.run_main(opener)
            self.assertEqual(code, 0 if error is None else 1)
            self.assertEqual(len(opener.requests), 2 if error is None else 10)
            for request in opener.requests:
                self.assertEqual(request.get_method(), 'GET')
                self.assertEqual(request.get_header('User-agent'),
                                 'AIEngineerPortal-HealthCheck/1.0')
                self.assertEqual(request.full_url, MODULE.ORIGIN + (
                    '/health' if request.get_header('Accept') == 'application/json' else '/'))
                self.assertIn(request.get_header('Accept'), ('application/json', 'text/html'))

    def test_certificate_and_network_errors_fail_closed_with_bounded_retries(self):
        for error in (ssl.SSLError(SENTINEL), TimeoutError(SENTINEL), ValueError(SENTINEL)):
            with self.subTest(error=type(error)):
                opener = Opener(error)
                code, sleep = self.run_main(opener)
                self.assertEqual(code, 1)
                self.assertEqual(len(opener.calls), 10)
                self.assertEqual(sleep.call_count, 4)

    def test_tls_defaults_verify_peer_and_redirects_are_refused(self):
        context = ssl.create_default_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        with patch.object(MODULE.ssl, 'create_default_context', return_value=context) as create, \
             patch.object(MODULE.urllib.request, 'build_opener', return_value=Opener()) as build:
            self.assertEqual(MODULE.main(), 0)
        create.assert_called_once()
        self.assertIs(build.call_args.args[0]._context, context)
        redirect = build.call_args.args[1]
        self.assertIsInstance(redirect, MODULE.NoRedirects)
        self.assertIsNone(redirect.redirect_request(None, None, 302, '', {}, 'http://other.example'))

    def test_bad_health_status_type_and_body_are_rejected(self):
        cases = [(b'{"status":"ok"}', 'application/json', 503),
                 (b'{"status":"ok"}', 'text/html', 200),
                 (b'{"status":"bad"}', 'application/json', 200),
                 (b'not json', 'application/json', 200),
                 (b' ' * 65537, 'application/json', 200)]
        for body, kind, status in cases:
            with self.subTest(kind=kind, status=status), \
                 patch.object(Opener, 'open', return_value=Response(body, kind, status)):
                with self.assertRaises(Exception):
                    MODULE.probe(Opener(), '/health', 'application/json')

    def test_non_html_root_is_rejected(self):
        with patch.object(Opener, 'open', return_value=Response(b'not html', 'text/html')):
            with self.assertRaises(ValueError):
                MODULE.probe(Opener(), '/', 'text/html')

    def test_workflow_pins_both_ssh_steps_and_runs_smoke_after_health(self):
        workflow = (ROOT / '.github/workflows/deploy.yml').read_text()
        trusted = 'SHA256:5l+l4ylrZutSMsq0T8rtMv5jF6cDPm6XtcnbwWWNSX4'
        self.assertEqual(workflow.count('uses: appleboy/ssh-action@v1.2.0'), 4)
        self.assertEqual(workflow.count('fingerprint: ' + trusted), 4)
        self.assertLess(workflow.index('- name: Verify health via SSH'),
                        workflow.index('- name: Verify public HTTPS endpoints'))
        self.assertIn('run: python3 -B scripts/public-smoke.py', workflow)
        self.assertNotIn('continue-on-error', workflow)



    def test_safe_failure_categories_do_not_echo_exception_details(self):
        import socket
        import urllib.error
        cases = [
            (ssl.SSLError(SENTINEL), 'tls_error', None),
            (urllib.error.URLError(ssl.SSLError(SENTINEL)), 'tls_error', None),
            (urllib.error.URLError(socket.gaierror(SENTINEL)), 'dns_error', None),
            (TimeoutError(SENTINEL), 'timeout', None),
            (ConnectionRefusedError(SENTINEL), 'connection_error', None),
            (ValueError(SENTINEL), 'probe_error', None),
            (urllib.error.HTTPError('https://' + SENTINEL, 503, SENTINEL, {}, None), 'http_status', 503),
            (urllib.error.HTTPError('https://' + SENTINEL, 302, SENTINEL, {'Location': SENTINEL}, None), 'redirect_refused', 302),
        ]
        for error, category, status in cases:
            with self.subTest(category=category):
                self.assertEqual(MODULE.classify(error), (category, status))
                code, _ = self.run_main(Opener(error))
                self.assertEqual(code, 1)
                self.assertIn('endpoint=health category=' + category, self.output)
                self.assertIn('endpoint=frontend category=' + category, self.output)
                self.assertNotIn(SENTINEL, self.output)

    def test_health_failure_does_not_hide_frontend_result(self):
        opener = Opener()
        def response(request, timeout):
            opener.calls.append(request.full_url)
            if request.full_url.endswith('/health'):
                return Response(b'private body', 'text/html')
            return Response(b'not html', 'text/html')
        with patch.object(opener, 'open', side_effect=response):
            code, _ = self.run_main(opener)
        self.assertEqual(code, 1)
        self.assertIn('endpoint=health category=content_type', self.output)
        self.assertIn('endpoint=frontend category=frontend_body', self.output)
        self.assertEqual(len(opener.calls), 10)

    def test_diagnostic_only_workflow_has_no_server_access(self):
        workflow = (ROOT / '.github/workflows/public-smoke.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertIn('contents: read', workflow)
        self.assertIn('python3 -B scripts/public-smoke.py', workflow)
        for forbidden in ('secrets.', 'ssh-action', 'deploy.yml', 'push:', 'pull_request:', 'packages:', 'write', 'inputs:'):
            self.assertNotIn(forbidden, workflow)


if __name__ == '__main__':
    unittest.main()
