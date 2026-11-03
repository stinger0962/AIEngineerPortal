"""Temporary state and mocked commands only; never execute Docker or production."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('rollback', ROOT / 'scripts/release-image-state.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CANDIDATE, PREVIOUS = 'a' * 40, 'b' * 40
IMAGES = {'backend': 'sha256:' + 'c' * 64, 'frontend': 'sha256:' + 'd' * 64}
SECRET = 'must-not-be-logged'


class ReleaseImageStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / 'app'
        (self.app / 'infra').mkdir(parents=True)
        (self.app / 'infra/docker-compose.prod.yml').write_text('fixture')
        self.state = self.root / 'state'
        for name, value in [('APP', self.app), ('STATE', self.state)]:
            patcher = patch.object(MODULE, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.calls = []

    def command(self, args, **kwargs):
        self.calls.append(args)
        if args[0] == 'git':
            return PREVIOUS
        command = args[len(MODULE.DOCKER):]
        if command[0] == 'inspect':
            service = command[-1].split('-')[1]
            return f'"{IMAGES[service]}" "running" "healthy"'
        if command[:2] == ['image', 'inspect']:
            return command[-1]
        if command[0] in ('tag', 'compose'):
            return ''
        self.fail('Unexpected command')

    def make_record(self):
        with patch.object(MODULE, 'command', side_effect=self.command):
            return MODULE.record(CANDIDATE)

    def test_record_captures_current_healthy_images_without_overwriting(self):
        data = self.make_record()
        self.assertEqual(data['images'], IMAGES)
        self.assertEqual(data['previous_sha'], PREVIOUS)
        self.assertEqual(MODULE.read_state(CANDIDATE), data)
        self.assertEqual((self.state / (CANDIDATE + '.json')).stat().st_mode & 0o777, 0o600)
        with patch.object(MODULE, 'command', side_effect=self.command):
            with self.assertRaises(FileExistsError):
                MODULE.record(CANDIDATE)
        self.assertFalse(any('tag' in call or 'compose' in call for call in self.calls))

    def test_prepare_rerun_preserves_original_images_without_recapture(self):
        original = self.make_record()
        path = self.state / (CANDIDATE + '.json')
        before = path.read_bytes()
        with patch.object(MODULE, 'command', side_effect=self.command), \
             patch.object(MODULE, 'inspect_container') as inspect:
            self.assertEqual(MODULE.prepare(CANDIDATE), original)
            inspect.assert_not_called()
        self.assertEqual(path.read_bytes(), before)

    def test_prepare_missing_record_captures_but_corrupt_record_fails_closed(self):
        with patch.object(MODULE, 'command', side_effect=self.command):
            MODULE.prepare(CANDIDATE)
        path = self.state / (CANDIDATE + '.json')
        path.write_text('corrupt')
        with patch.object(MODULE, 'record') as record:
            with self.assertRaises(ValueError):
                MODULE.prepare(CANDIDATE)
            record.assert_not_called()

    def test_rollback_uses_only_recorded_local_images_and_application_services(self):
        self.make_record()
        self.calls = []
        with patch.object(MODULE, 'command', side_effect=self.command):
            MODULE.rollback(CANDIDATE)
        tags = [call for call in self.calls if 'tag' in call]
        self.assertEqual(tags, [MODULE.DOCKER + ['tag', IMAGES[s], 'infra-' + s + ':latest']
                                for s in MODULE.SERVICES])
        compose = next(call for call in self.calls if 'compose' in call)
        self.assertEqual(compose[-2:], ['backend', 'frontend'])
        for option in ('--no-deps', '--no-build', '--force-recreate'):
            self.assertIn(option, compose)
        self.assertEqual(compose[compose.index('--pull') + 1], 'never')
        for forbidden in ('down', '-v', '--volumes', 'prune', 'rm', 'pg_restore', 'checkout'):
            self.assertFalse(any(forbidden in call for call in self.calls))
        self.assertFalse(any(call[0] == 'git' for call in self.calls))

    def test_tampered_refs_candidate_and_fields_fail_before_commands(self):
        valid = self.make_record()
        cases = []
        for key, value in [('candidate_sha', 'e' * 40), ('previous_sha', 'bad'),
                           ('compose_sha256', 'f' * 64), ('version', True)]:
            data = copy.deepcopy(valid)
            data[key] = value
            cases.append(data)
        data = copy.deepcopy(valid)
        data['images']['backend'] = 'untrusted.example/image:latest'
        cases.append(data)
        data = copy.deepcopy(valid)
        data['credential'] = SECRET
        cases.append(data)
        path = self.state / (CANDIDATE + '.json')
        for data in cases:
            with self.subTest(data=data):
                path.write_text(json.dumps(data))
                with patch.object(MODULE, 'command') as command:
                    with self.assertRaises(ValueError):
                        MODULE.rollback(CANDIDATE)
                    command.assert_not_called()

    def test_missing_local_image_fails_before_any_tag_or_recreate(self):
        self.make_record()
        self.calls = []
        def missing(args, **kwargs):
            if args[-1] == IMAGES['frontend']:
                raise ValueError(SECRET)
            return self.command(args, **kwargs)
        with patch.object(MODULE, 'command', side_effect=missing):
            with self.assertRaises(ValueError):
                MODULE.rollback(CANDIDATE)
        self.assertFalse(any('tag' in call or 'compose' in call for call in self.calls))

    def test_changed_compose_or_unsafe_state_permissions_fail_closed(self):
        self.make_record()
        path = self.state / (CANDIDATE + '.json')
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            MODULE.read_state(CANDIDATE)
        path.chmod(0o600)
        (self.app / 'infra/docker-compose.prod.yml').write_text('changed volume layout')
        with self.assertRaises(ValueError):
            MODULE.read_state(CANDIDATE)

    def test_state_symlink_is_not_followed(self):
        self.make_record()
        path = self.state / (CANDIDATE + '.json')
        saved = self.state / 'saved'
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaises(OSError):
            MODULE.read_state(CANDIDATE)

    def test_unhealthy_rollback_fails_at_monotonic_deadline(self):
        self.make_record()
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        with patch.object(MODULE, 'command', side_effect=self.command), \
             patch.object(MODULE, 'inspect_container', return_value=(IMAGES['backend'], 'running', 'unhealthy')), \
             patch.object(MODULE.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(MODULE.time, 'sleep', side_effect=sleep):
            with self.assertRaises(ValueError):
                MODULE.rollback(CANDIDATE)
        self.assertEqual(clock[0], MODULE.HEALTH_TIMEOUT_SECONDS)

    def test_delayed_healthy_startup_beyond_old_timeout_succeeds(self):
        self.make_record()
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        def inspect(service, timeout=30):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 10)
            return IMAGES[service], 'running', 'healthy' if clock[0] >= 75 else 'starting'
        with patch.object(MODULE, 'command', side_effect=self.command), \
             patch.object(MODULE, 'inspect_container', side_effect=inspect), \
             patch.object(MODULE.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(MODULE.time, 'sleep', side_effect=sleep):
            MODULE.rollback(CANDIDATE)
        self.assertEqual(clock[0], 75)

    def test_concurrent_helper_operation_fails_closed(self):
        with MODULE.operation_lock(create=True):
            with self.assertRaises(BlockingIOError):
                with MODULE.operation_lock():
                    self.fail('Concurrent operation acquired the lock')

    def test_entrypoint_rejects_arbitrary_args_and_redacts_failures(self):
        for args in (['rollback', '../bad'], ['pull', CANDIDATE], ['rollback']):
            with patch.object(MODULE, 'rollback') as rollback:
                self.assertEqual(MODULE.main(args), 1)
                rollback.assert_not_called()
        output = io.StringIO()
        with patch.object(MODULE, 'rollback', side_effect=RuntimeError(SECRET)), contextlib.redirect_stdout(output):
            self.assertEqual(MODULE.main(['rollback', CANDIDATE]), 1)
        self.assertNotIn(SECRET, output.getvalue())


if __name__ == '__main__':
    unittest.main()
