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
        self.home = self.root / 'home'
        self.home.mkdir()
        account = type('Account', (), {'pw_dir': str(self.home)})()
        patcher = patch.object(MODULE.pwd, 'getpwuid', return_value=account)
        patcher.start()
        self.addCleanup(patcher.stop)
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

    def test_automatic_capture_is_once_per_sha_even_after_rollback(self):
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': MODULE.compose_hash()}), \
             patch.object(MODULE, 'command', side_effect=self.command):
            self.assertEqual(MODULE.main(['prepare-auto', CANDIDATE]), 0)
            path = self.state / (CANDIDATE + '.json')
            original = path.read_bytes()
            self.assertEqual(MODULE.main(['prepare-auto', CANDIDATE]), 1)
            MODULE.rollback(CANDIDATE)
            self.calls.clear()
            self.assertEqual(MODULE.main(['prepare-auto', CANDIDATE]), 1)
            self.assertFalse(any('tag' in call or 'compose' in call for call in self.calls))
            self.assertEqual(path.read_bytes(), original)
            # Deliberate manual recovery can reuse the original rollback point.
            self.assertEqual(MODULE.main(['prepare', CANDIDATE]), 0)

    def test_automatic_run_queued_behind_manual_rollback_fails_closed(self):
        self.make_record()
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': MODULE.compose_hash()}), \
             patch.object(MODULE, 'command', side_effect=self.command):
            MODULE.rollback(CANDIDATE)
            self.calls.clear()
            self.assertEqual(MODULE.main(['prepare-auto', CANDIDATE]), 1)
        self.assertFalse(any('tag' in call or 'compose' in call for call in self.calls))

    def test_automatic_partial_record_is_never_overwritten(self):
        self.make_record()
        path = self.state / (CANDIDATE + '.json')
        path.write_text('{"partial":')
        before = path.read_bytes()
        self.calls.clear()
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': MODULE.compose_hash()}), \
             patch.object(MODULE, 'command', side_effect=self.command):
            self.assertEqual(MODULE.main(['prepare-auto', CANDIDATE]), 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(any('tag' in call or 'compose' in call for call in self.calls))

    def test_automatic_compose_mismatch_stops_before_capture(self):
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': 'f' * 64}), \
             patch.object(MODULE, 'record') as record:
            self.assertEqual(MODULE.main(['prepare-auto', CANDIDATE]), 1)
            record.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_prepare_cli_rejects_candidate_compose_mismatch_before_mutation(self):
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': 'f' * 64}), \
             patch.object(MODULE, 'prepare') as prepare:
            self.assertEqual(MODULE.main(['prepare', CANDIDATE]), 1)
            prepare.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_prepare_cli_accepts_exact_candidate_compose(self):
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': MODULE.compose_hash()}), \
             patch.object(MODULE, 'command', side_effect=self.command):
            self.assertEqual(MODULE.main(['prepare', CANDIDATE]), 0)
        self.assertEqual(MODULE.read_state(CANDIDATE)['images'], IMAGES)

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


    def run_prepare_output(self, **patches):
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': MODULE.compose_hash()}))
            stack.enter_context(contextlib.redirect_stdout(output))
            for name, value in patches.items():
                stack.enter_context(patch.object(MODULE, name, side_effect=value))
            result = MODULE.main(['prepare', CANDIDATE])
        return result, output.getvalue()

    def test_diagnostics_identify_git_failure_without_command_output(self):
        result, output = self.run_prepare_output(command=ValueError('command_failed'))
        self.assertEqual(result, 1)
        self.assertEqual(output, 'Release image state: operation failed stage=previous_commit category=command_failed\n')
        self.assertFalse((self.state / (CANDIDATE + '.json')).exists())

    def test_diagnostics_identify_container_and_image_failures(self):
        for target, expected in [('inspect', 'container_inspection'), ('image', 'local_image_check')]:
            def failing(args, **kwargs):
                if args[0] != 'git' and args[len(MODULE.DOCKER)] == target:
                    raise PermissionError(SECRET)
                return self.command(args, **kwargs)
            with self.subTest(target=target):
                result, output = self.run_prepare_output(command=failing)
                self.assertEqual(result, 1)
                self.assertEqual(output, 'Release image state: operation failed stage=' + expected + ' category=permission_denied\n')
                self.assertNotIn(SECRET, output)
                self.assertFalse(any('tag' in c or 'compose' in c for c in self.calls))

    def test_diagnostics_candidate_mismatch_before_state_writes(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': 'f' * 64}), contextlib.redirect_stdout(output):
            self.assertEqual(MODULE.main(['prepare', CANDIDATE]), 1)
        self.assertIn('stage=candidate_compatibility category=candidate_compose_incompatible', output.getvalue())
        self.assertFalse(self.state.exists())

    def test_diagnostics_bad_state_does_not_recapture(self):
        self.make_record()
        (self.state / (CANDIDATE + '.json')).write_text(SECRET)
        result, output = self.run_prepare_output(command=AssertionError('must not execute'))
        self.assertEqual(result, 1)
        self.assertEqual(output, 'Release image state: operation failed stage=state_read category=invalid_json\n')
        self.assertNotIn(SECRET, output)

    def test_diagnostics_lock_contention_and_permissions(self):
        with MODULE.operation_lock(create=True):
            result, output = self.run_prepare_output()
        self.assertEqual(result, 1)
        self.assertIn('stage=state_lock category=lock_unavailable', output)
        self.state.chmod(0o755)
        result, output = self.run_prepare_output()
        self.assertEqual(result, 1)
        self.assertIn('stage=state_directory category=unsafe_state_permissions', output)

    def test_category_allowlist_never_echoes_arbitrary_values(self):
        import subprocess
        cases = [
            (PermissionError(SECRET), 'permission_denied'),
            (FileNotFoundError(SECRET), 'not_found'),
            (FileExistsError(SECRET), 'already_exists'),
            (BlockingIOError(SECRET), 'lock_unavailable'),
            (subprocess.TimeoutExpired(SECRET, 30, output=SECRET, stderr=SECRET), 'command_timeout'),
            (OSError(SECRET), 'filesystem_error'),
            (ValueError(SECRET), 'operation_failed'),
            (ValueError(['unsafe_path']), 'operation_failed'),
            (RuntimeError(SECRET), 'operation_failed'),
        ]
        for exc, category in cases:
            self.assertEqual(MODULE.failure_category(exc), category)
        for reason in MODULE.REASONS:
            self.assertEqual(MODULE.failure_category(ValueError(reason)), reason)

    def test_diagnostics_invalid_stage_redacted_and_fail_closed(self):
        exc = RuntimeError(SECRET)
        exc._release_stage = SECRET
        result, output = self.run_prepare_output(prepare=exc)
        self.assertEqual(result, 1)
        self.assertEqual(output, 'Release image state: operation failed stage=operation category=operation_failed\n')
        self.assertNotIn(SECRET, output)



    def test_git_stderr_categories_are_fixed_and_never_echoed(self):
        cases = [
            ("fatal: detected dubious ownership in repository at '/private/" + SECRET + "'\n", 'git_dubious_ownership'),
            ('fatal: not a git repository (or any of the parent directories): .git\n' + SECRET, 'git_not_repository'),
            ("fatal: cannot change to '/private/" + SECRET + "': Permission denied\n", 'git_permission_denied'),
            ('fatal: unknown problem ' + SECRET, 'git_command_failed'),
            ('noise ' + SECRET + ' dubious ownership', 'git_command_failed'),
            ('x' * 4096 + '\nfatal: not a git repository', 'git_command_failed'),
            (None, 'git_command_failed'),
        ]
        for stderr, category in cases:
            with self.subTest(category=category):
                self.assertEqual(MODULE.git_failure_category(stderr), category)
                result = type('Result', (), {'returncode': 128, 'stdout': SECRET, 'stderr': stderr})()
                output = io.StringIO()
                with patch.object(MODULE.subprocess, 'run', return_value=result) as run, \
                     patch.dict(os.environ, {'EXPECTED_COMPOSE_SHA256': MODULE.compose_hash()}), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(MODULE.main(['prepare', CANDIDATE]), 1)
                self.assertEqual(output.getvalue(), 'Release image state: operation failed stage=previous_commit category=' + category + '\n')
                self.assertNotIn(SECRET, output.getvalue())
                self.assertEqual(run.call_args.kwargs['env'], dict(MODULE.ENV, HOME=str(self.home)))
                self.assertEqual(run.call_args.kwargs['stderr'], MODULE.subprocess.PIPE)
                self.assertEqual(run.call_args.args[0], ['git', '--no-optional-locks', '-C', str(self.app), 'rev-parse', 'HEAD'])
                self.assertFalse((self.state / (CANDIDATE + '.json')).exists())

    def test_non_git_commands_still_discard_stderr(self):
        result = type('Result', (), {'returncode': 1, 'stdout': SECRET})()
        with patch.object(MODULE.subprocess, 'run', return_value=result) as run:
            with self.assertRaisesRegex(ValueError, '^command_failed$'):
                MODULE.command(MODULE.DOCKER + ['inspect', 'fixture'])
        self.assertEqual(run.call_args.kwargs['stderr'], MODULE.subprocess.DEVNULL)

    def test_successful_git_read_uses_only_verified_account_home(self):
        result = type('Result', (), {'returncode': 0, 'stdout': PREVIOUS + '\n', 'stderr': SECRET})()
        with patch.object(MODULE.subprocess, 'run', return_value=result) as run:
            self.assertEqual(MODULE.command(['git', '--no-optional-locks', '-C', str(self.app), 'rev-parse', 'HEAD']), PREVIOUS)
        self.assertEqual(run.call_args.kwargs['env'], dict(MODULE.ENV, HOME=str(self.home)))
        self.assertNotIn('safe.directory', str(run.call_args))



    def test_git_home_comes_from_os_account_not_inherited_environment(self):
        with patch.dict(os.environ, {'HOME': '/untrusted', 'XDG_CONFIG_HOME': '/untrusted',
                                   'GIT_CONFIG_GLOBAL': '/untrusted', 'GIT_CONFIG_COUNT': '1',
                                   'SUDO_UID': '12345', 'DOCKER_HOST': 'tcp://untrusted'}):
            self.assertEqual(MODULE.git_environment(), dict(MODULE.ENV, HOME=str(self.home)))
        MODULE.pwd.getpwuid.assert_called_with(os.geteuid())

    def test_invalid_account_home_fails_before_git_execution(self):
        link = self.root / 'link'
        link.symlink_to(self.home)
        for value in ('relative', str(link), str(self.app / 'infra/docker-compose.prod.yml')):
            with self.subTest(value=value):
                account = type('Account', (), {'pw_dir': value})()
                with patch.object(MODULE.pwd, 'getpwuid', return_value=account), \
                     patch.object(MODULE.subprocess, 'run') as run:
                    with self.assertRaisesRegex(ValueError, 'invalid_account_home'):
                        MODULE.command(['git', '--no-optional-locks', '-C', str(self.app), 'rev-parse', 'HEAD'])
                    run.assert_not_called()

    def test_foreign_owned_account_home_fails_closed(self):
        info = type('Info', (), {'st_mode': 0o40700, 'st_uid': os.geteuid() + 1})()
        with patch.object(Path, 'lstat', return_value=info):
            with self.assertRaisesRegex(ValueError, 'invalid_account_home'):
                MODULE.git_environment()

    def test_docker_never_loads_account_home_or_git_configuration(self):
        result = type('Result', (), {'returncode': 0, 'stdout': 'fixture'})()
        with patch.object(MODULE.subprocess, 'run', return_value=result) as run, \
             patch.object(MODULE, 'git_environment', side_effect=AssertionError('not Git')):
            self.assertEqual(MODULE.command(MODULE.DOCKER + ['inspect', 'fixture']), 'fixture')
        self.assertEqual(run.call_args.kwargs['env'], MODULE.ENV)
        self.assertNotIn('HOME', run.call_args.kwargs['env'])


if __name__ == '__main__':
    unittest.main()
