"""Public smoke checks are fully mocked; no live site requests."""
import contextlib
from email.message import Message
import importlib.util
import io
from pathlib import Path
import ssl
import unittest
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
        self.error = error
    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        if self.error:
            raise self.error
        if request.full_url.endswith('/health'):
            return Response(b'{"status":"ok"}', 'application/json')
        return Response(b'<!doctype html><html></html>', 'text/html')


class PublicSmokeTests(unittest.TestCase):
    def run_main(self, opener):
        output = io.StringIO()
        with patch.object(MODULE.urllib.request, 'build_opener', return_value=opener), \
             patch.object(MODULE.time, 'sleep') as sleep, contextlib.redirect_stdout(output):
            code = MODULE.main()
        self.assertNotIn(SENTINEL, output.getvalue())
        return code, sleep

    def test_success_checks_only_fixed_https_urls_with_timeout(self):
        opener = Opener()
        code, sleep = self.run_main(opener)
        self.assertEqual(code, 0)
        self.assertEqual(opener.calls, [
            ('https://portal.leipan.cc/health', 10),
            ('https://portal.leipan.cc/', 10)])
        sleep.assert_not_called()

    def test_certificate_and_network_errors_fail_closed_with_bounded_retries(self):
        for error in (ssl.SSLError(SENTINEL), TimeoutError(SENTINEL), ValueError(SENTINEL)):
            with self.subTest(error=type(error)):
                opener = Opener(error)
                code, sleep = self.run_main(opener)
                self.assertEqual(code, 1)
                self.assertEqual(len(opener.calls), 5)
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


if __name__ == '__main__':
    unittest.main()
