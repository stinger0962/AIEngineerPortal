"""No live network, SSH authentication, host-key trust changes or server commands."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('observation', ROOT / 'scripts/observe-ssh-host-keys.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SECRET_HOST = 'private-target.example'
FINGERPRINT = 'SHA256:' + 'a' * 43


class HostObservationTests(unittest.TestCase):
    def address(self, ip):
        return (socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 22))

    def run_case(self, addresses=None, output=None, failure=None, host=SECRET_HOST):
        calls = []
        def execute(args, **kwargs):
            calls.append(args)
            self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
            self.assertEqual(kwargs['timeout'], 15)
            if failure:
                raise RuntimeError(SECRET_HOST + ' private-error-value')
            if args[0] == 'ssh-keyscan':
                self.assertEqual(args, ['ssh-keyscan', '-T', '5', '-p', '22', '-t',
                                       'ed25519,ecdsa,rsa', MODULE.EXPECTED_IP])
                value = output if output is not None else f'{SECRET_HOST} ssh-ed25519 YWJj\n'
            else:
                self.assertEqual(args, ['ssh-keygen', '-l', '-E', 'sha256', '-f', '/dev/stdin'])
                self.assertNotIn(SECRET_HOST, kwargs['input'])
                value = f'256 {FINGERPRINT} no comment (ED25519)\n'
            return subprocess.CompletedProcess(args, 0, value)
        stream = io.StringIO()
        with patch.dict(os.environ, {'VPS_HOST': host}, clear=True), \
             patch.object(MODULE.socket, 'getaddrinfo', return_value=addresses if addresses is not None else [self.address(MODULE.EXPECTED_IP)]) as resolve, \
             patch.object(MODULE.subprocess, 'run', side_effect=execute), contextlib.redirect_stdout(stream):
            code = MODULE.observe()
        self.assertNotIn(SECRET_HOST, stream.getvalue())
        self.assertNotIn(MODULE.EXPECTED_IP, stream.getvalue())
        self.assertNotIn('private-error-value', stream.getvalue())
        return code, json.loads(stream.getvalue()), calls, resolve

    def test_matching_target_outputs_only_public_key_metadata(self):
        code, report, calls, resolve = self.run_case()
        self.assertEqual(code, 0)
        self.assertEqual(report, {'expected_ip_match': True, 'observed_public_keys': [
            {'type': 'ssh-ed25519', 'fingerprint': FINGERPRINT}]})
        self.assertEqual(len(calls), 2)
        resolve.assert_called_once_with(SECRET_HOST, 22, type=socket.SOCK_STREAM)

    def test_confirmed_portal_ip_is_the_only_allowed_target(self):
        self.assertEqual(MODULE.EXPECTED_IP, '146.190.124.162')
        code, report, calls, _ = self.run_case(
            host='146.190.124.162', addresses=[self.address('146.190.124.162')])
        self.assertEqual(code, 0)
        self.assertTrue(report['expected_ip_match'])
        self.assertEqual(calls[0][-1], '146.190.124.162')

    def test_stock_tracker_ip_is_rejected_before_probe(self):
        for addresses in ([self.address('64.225.43.230')],
                          [self.address('146.190.124.162'), self.address('64.225.43.230')]):
            with self.subTest(addresses=addresses):
                code, report, calls, _ = self.run_case(addresses=addresses)
                self.assertEqual(code, 1)
                self.assertFalse(report['expected_ip_match'])
                self.assertEqual(report['observed_public_keys'], [])
                self.assertEqual(calls, [])

    def test_mismatch_empty_or_mixed_dns_stops_before_probe(self):
        for addresses in ([], [self.address('192.0.2.1')],
                          [self.address(MODULE.EXPECTED_IP), self.address('192.0.2.1')]):
            with self.subTest(addresses=addresses):
                code, report, calls, _ = self.run_case(addresses=addresses)
                self.assertEqual(code, 1)
                self.assertFalse(report['expected_ip_match'])
                self.assertEqual(calls, [])

    def test_invalid_target_stops_before_dns_and_probe(self):
        for host in ('', '-option', '$(command)', 'one,two', 'host:2222'):
            with self.subTest(host=host):
                code, _, calls, resolve = self.run_case(host=host)
                self.assertEqual(code, 1)
                self.assertEqual(calls, [])
                resolve.assert_not_called()

    def test_network_failure_is_redacted_and_fails_closed(self):
        code, report, calls, _ = self.run_case(failure=True)
        self.assertEqual(code, 1)
        self.assertTrue(report['expected_ip_match'])
        self.assertEqual(report['observed_public_keys'], [])
        self.assertEqual(len(calls), 1)

    def test_missing_or_malformed_key_output_fails_closed(self):
        for output in ('', SECRET_HOST + ' ssh-bad YWJj', SECRET_HOST + ' ssh-rsa !bad!'):
            with self.subTest(output=output):
                code, report, _, _ = self.run_case(output=output)
                self.assertEqual(code, 1)
                self.assertEqual(report['observed_public_keys'], [])

    def test_workflow_keeps_observation_separate_from_trust(self):
        workflow = (ROOT / '.github/workflows/production-preflight.yml').read_text()
        before, ssh = workflow.split('      - name: Inspect fixed production metadata', 1)
        observation = before.split('      - name: Observe public host keys', 1)[1]
        self.assertIn('VPS_HOST: ${{ secrets.VPS_HOST }}', observation)
        self.assertNotIn('VPS_SSH_KEY', observation)
        self.assertNotIn('continue-on-error', workflow)
        self.assertIn('fingerprint: ${{ inputs.host_fingerprint }}', ssh)
        self.assertNotIn('outputs.', ssh)


if __name__ == '__main__':
    unittest.main()
