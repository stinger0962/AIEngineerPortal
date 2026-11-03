"""Production inspection tests: subprocess mocks and temporary files only."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / 'scripts/production-preflight.sh').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
REVISION = 'a' * 40
IMAGE = 'sha256:' + 'b' * 64
DIGEST = 'sha256:' + 'c' * 64
SENTINEL = 'secret-value-must-never-appear'


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.module = {'__name__': 'preflight_test'}
        exec(compile(SOURCE, 'preflight', 'exec'), self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name)
        self.module['APP'] = self.app
        (self.app / 'backups').mkdir()
        (self.app / 'backups/portal_old.dump').write_bytes(b'old')
        (self.app / 'backups/portal_new.dump').write_bytes(b'new backup')
        os.utime(self.app / 'backups/portal_old.dump', (1, 1))
        os.utime(self.app / 'backups/portal_new.dump', (2, 2))
        (self.app / 'backups/portal_link.dump').symlink_to('/nonexistent')
        (self.app / 'backups/ignored.txt').write_text(SENTINEL)
        self.commands = []

    def mock_run(self, args, **kwargs):
        self.commands.append(args)
        self.assertIs(kwargs['stdin'], subprocess.DEVNULL)
        self.assertIs(kwargs['stderr'], subprocess.DEVNULL)
        self.assertEqual(kwargs['timeout'], 10)
        if args == ['git', '--no-optional-locks', '-C', str(self.app), 'rev-parse', 'HEAD']:
            output = REVISION
        elif args[:3] == ['docker', 'inspect', '--format'] and args[-1] in [f'infra-{s}-1' for s in self.module['SERVICES']]:
            self.assertNotIn('.Config.Env', args[3])
            self.assertNotIn('.Log', args[3])
            output = f'"running" "healthy" "{IMAGE}"'
        elif args == ['docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', IMAGE]:
            output = json.dumps([f'private/{SENTINEL}@{DIGEST}'])
        elif args == ['docker', 'exec', 'infra-backend-1', 'python', '-B', '-c', self.module['FLAGS_PROGRAM']]:
            output = json.dumps({'STRIPE_TEST_ENABLED': 'unset', 'ZIWEI_REQUIRE_CREDITS': 'false',
                                 'STRIPE_SECRET_KEY': 'present', 'STRIPE_WEBHOOK_SECRET': 'absent'})
        else:
            self.fail(f'Unapproved command shape: {args[:3]}')
        return subprocess.CompletedProcess(args, 0, stdout=output)

    def run_report(self, mock):
        output = io.StringIO()
        with patch('subprocess.run', side_effect=mock), contextlib.redirect_stdout(output):
            result = self.module['main']()
        self.assertNotIn(SENTINEL, output.getvalue())
        return result, json.loads(output.getvalue())

    def test_only_fixed_read_commands_and_sanitized_metadata(self):
        before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (self.app / 'backups').iterdir() if not p.is_symlink()}
        result, report = self.run_report(self.mock_run)
        self.assertEqual(result, 0)
        self.assertEqual(report['deployed_revision'], REVISION)
        self.assertEqual(report['backend']['registry_digests'], [DIGEST])
        self.assertEqual(report['backups']['count'], 2)
        self.assertEqual(report['backups']['latest_bytes'], 10)
        self.assertEqual(report['backups']['latest_utc'], '1970-01-01T00:00:02+00:00')
        self.assertFalse(report['backups']['restore_verified'])
        after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in (self.app / 'backups').iterdir() if not p.is_symlink()}
        self.assertEqual(before, after)
        self.assertEqual(len(self.commands), 12)

    def test_failures_do_not_disclose_errors_and_continue_other_checks(self):
        def fail(args, **kwargs):
            if args[0] == 'git':
                raise RuntimeError(SENTINEL)
            return self.mock_run(args, **kwargs)
        result, report = self.run_report(fail)
        self.assertEqual(result, 1)
        self.assertEqual(report['deployed_revision'], {'error': 'unavailable'})
        self.assertEqual(report['backend']['health'], 'healthy')

    def test_unexpected_output_is_not_logged(self):
        def corrupt(args, **kwargs):
            result = self.mock_run(args, **kwargs)
            if args[:2] == ['docker', 'exec']:
                result.stdout = SENTINEL
            return result
        result, report = self.run_report(corrupt)
        self.assertEqual(result, 1)
        self.assertEqual(report['payment_environment'], {'error': 'unavailable'})

    def test_empty_backup_directory_is_not_reported_as_verified(self):
        for p in (self.app / 'backups').iterdir():
            p.unlink()
        result, report = self.run_report(self.mock_run)
        self.assertEqual(result, 0)
        self.assertEqual(report['backups'], dict(count=0, latest_utc=None, latest_bytes=None, restore_verified=False))

    def assert_backup_error(self, expected):
        result, report = self.run_report(self.mock_run)
        self.assertEqual(result, 1)
        self.assertEqual(report['backups'], {'error': expected, 'restore_verified': False})
        self.assertEqual(report['backend']['health'], 'healthy')
        self.assertNotIn(str(self.app), json.dumps(report))

    def remove_backup_directory(self):
        for item in (self.app / 'backups').iterdir():
            item.unlink()
        (self.app / 'backups').rmdir()

    def test_missing_backup_directory_fails_without_creating_it(self):
        self.remove_backup_directory()
        self.assert_backup_error('directory_missing')
        self.assertFalse((self.app / 'backups').exists())

    def test_symlink_backup_directory_is_rejected(self):
        self.remove_backup_directory()
        (self.app / 'backups').symlink_to(self.app, target_is_directory=True)
        self.assert_backup_error('symlink_rejected')

    def test_backup_path_that_is_a_file_is_rejected(self):
        self.remove_backup_directory()
        (self.app / 'backups').write_text(SENTINEL)
        self.assert_backup_error('invalid_directory')
        self.assertEqual((self.app / 'backups').read_text(), SENTINEL)

    def test_backup_scan_failures_have_fixed_redacted_labels(self):
        cases = [(FileNotFoundError(SENTINEL), 'directory_missing'),
                 (PermissionError(SENTINEL), 'permission_denied'),
                 (NotADirectoryError(SENTINEL), 'invalid_directory'),
                 (OSError(SENTINEL), 'metadata_unavailable')]
        for error, expected in cases:
            with self.subTest(expected=expected), patch('os.scandir', side_effect=error):
                self.assert_backup_error(expected)

    def test_backup_entry_metadata_failure_is_not_directory_missing(self):
        class BrokenEntry:
            name = 'portal_test.dump'
            def is_file(self, **kwargs):
                return True
            def stat(self, **kwargs):
                raise FileNotFoundError(SENTINEL)
        class Entries:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def __iter__(self):
                return iter([BrokenEntry()])
        with patch('os.scandir', return_value=Entries()):
            self.assert_backup_error('metadata_unavailable')

    def test_environment_program_never_prints_values_except_boolean_flags(self):
        output = io.StringIO()
        env = {'STRIPE_TEST_ENABLED': SENTINEL, 'ZIWEI_REQUIRE_CREDITS': 'FALSE',
               'STRIPE_SECRET_KEY': SENTINEL, 'STRIPE_WEBHOOK_SECRET': SENTINEL}
        with patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(output):
            exec(self.module['FLAGS_PROGRAM'])
        self.assertNotIn(SENTINEL, output.getvalue())
        self.assertEqual(json.loads(output.getvalue()), {'STRIPE_TEST_ENABLED': 'non_boolean',
                         'ZIWEI_REQUIRE_CREDITS': 'false', 'STRIPE_SECRET_KEY': 'present',
                         'STRIPE_WEBHOOK_SECRET': 'present'})

    def test_fingerprint_validation_fails_closed_without_echoing_input(self):
        for value in ('', SENTINEL, 'SHA256:' + 'a' * 42, 'SHA256:' + 'a' * 43 + '\n', '$(false)'):
            with self.subTest(value=value):
                result = subprocess.run(['bash', str(ROOT / 'scripts/validate-ssh-fingerprint.sh')],
                                        env={**os.environ, 'HOST_FINGERPRINT': value}, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(SENTINEL, result.stderr)
        result = subprocess.run(['bash', str(ROOT / 'scripts/validate-ssh-fingerprint.sh')],
                                env={**os.environ, 'HOST_FINGERPRINT': 'SHA256:' + 'a' * 43}, capture_output=True)
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
