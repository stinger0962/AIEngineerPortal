"""Release-gate tests use mocked API calls only; no network or deployment."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('gate', ROOT / 'scripts/require-release-ci.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = 'a' * 40
TOKEN = 'never-log-this-token'


def run_record(**changes):
    record = dict(id=1, head_sha=SHA, head_branch='main', event='push',
                  path=MODULE.WORKFLOW, status='completed', conclusion='success',
                  head_repository={'full_name': MODULE.REPOSITORY})
    record.update(changes)
    return record


class ReleaseGateTests(unittest.TestCase):
    def test_only_exact_main_push_ci_is_eligible(self):
        self.assertEqual(MODULE.evaluate_runs([run_record()], SHA), 'success')
        for changes in ({'head_sha': 'b' * 40}, {'head_branch': 'feature'},
                        {'event': 'pull_request'}, {'path': '.github/workflows/other.yml'},
                        {'head_repository': {'full_name': 'another/repo'}}):
            with self.subTest(changes=changes):
                self.assertEqual(MODULE.evaluate_runs([run_record(**changes)], SHA), 'pending')

    def test_latest_run_must_complete_successfully(self):
        for conclusion in ('failure', 'cancelled', 'skipped', 'neutral', None):
            self.assertEqual(MODULE.evaluate_runs([
                run_record(), run_record(id=2, conclusion=conclusion)], SHA), 'failed')
        self.assertEqual(MODULE.evaluate_runs([
            run_record(), run_record(id=2, status='in_progress')], SHA), 'pending')

    def test_stale_commit_stops_before_querying_ci(self):
        with patch.object(MODULE, 'request_json', return_value={'commit': {'sha': 'b' * 40}}) as request:
            self.assertEqual(MODULE.check(SHA, TOKEN), 'stale')
        request.assert_called_once_with('/branches/main', TOKEN)

    def test_api_queries_are_fixed_and_paginated(self):
        responses = [{'commit': {'sha': SHA}},
                     {'workflow_runs': [run_record(path='other')] * 100},
                     {'workflow_runs': [run_record()]}]
        with patch.object(MODULE, 'request_json', side_effect=responses) as request:
            self.assertEqual(MODULE.check(SHA, TOKEN), 'success')
        self.assertEqual(len(request.call_args_list), 3)
        self.assertIn('page=2', request.call_args_list[-1].args[0])

    def run_main(self, result=None, error=None, env=None):
        stream = io.StringIO()
        context = {'GITHUB_SHA': SHA, 'GITHUB_REPOSITORY': MODULE.REPOSITORY,
                   'GH_TOKEN': TOKEN, 'GITHUB_EVENT_NAME': 'push',
                   'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ATTEMPT': '1'}
        context.update(env or {})
        with patch.dict(os.environ, context, clear=True), \
             patch.object(MODULE, 'ATTEMPTS', 2), \
             patch.object(MODULE, 'check', return_value=result, side_effect=error) as check, \
             patch.object(MODULE.time, 'sleep') as sleep, contextlib.redirect_stdout(stream):
            code = MODULE.main()
        self.assertNotIn(TOKEN, stream.getvalue())
        return code, check, sleep

    def test_errors_and_missing_context_fail_closed(self):
        self.assertEqual(self.run_main(error=RuntimeError(TOKEN))[0], 1)
        code, check, _ = self.run_main(env={'GH_TOKEN': ''})
        self.assertEqual(code, 1)
        check.assert_not_called()
        self.assertEqual(self.run_main(result='failed')[0], 1)
        self.assertEqual(self.run_main(result='stale')[0], 1)

    def test_wait_is_bounded_and_success_is_required(self):
        code, check, sleep = self.run_main(result='pending')
        self.assertEqual(code, 1)
        self.assertEqual(check.call_count, 2)
        sleep.assert_called_once_with(15)
        self.assertEqual(self.run_main(result='success')[0], 0)

    def test_untrusted_events_and_refs_stop_before_api(self):
        for event in ('pull_request', 'pull_request_target', 'workflow_run', 'schedule', ''):
            code, check, _ = self.run_main(env={'GITHUB_EVENT_NAME': event})
            self.assertEqual(code, 1)
            check.assert_not_called()
        for ref in ('refs/heads/feature', 'refs/tags/v1.0.0', ''):
            code, check, _ = self.run_main(env={'GITHUB_REF': ref})
            self.assertEqual(code, 1)
            check.assert_not_called()
        for attempt in ('2', '3', '', 'invalid'):
            code, check, _ = self.run_main(env={'GITHUB_RUN_ATTEMPT': attempt})
            self.assertEqual(code, 1)
            check.assert_not_called()
        self.assertEqual(self.run_main(result='success', env={
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '2'})[0], 0)

    def test_main_advancing_while_waiting_stops_release(self):
        responses = [{'commit': {'sha': SHA}}, {'workflow_runs': []},
                     {'commit': {'sha': 'b' * 40}}]
        with patch.object(MODULE, 'request_json', side_effect=responses):
            self.assertEqual(MODULE.check(SHA, TOKEN), 'pending')
            self.assertEqual(MODULE.check(SHA, TOKEN), 'stale')

    def test_incomplete_pagination_never_accepts_success(self):
        responses = [{'commit': {'sha': SHA}}] + [
            {'workflow_runs': [run_record()] * 100}] * 10
        with patch.object(MODULE, 'request_json', side_effect=responses):
            self.assertEqual(MODULE.check(SHA, TOKEN), 'failed')

    def test_release_wiring_has_one_automatic_main_trigger(self):
        deploy = (ROOT / '.github/workflows/deploy.yml').read_text()
        trigger = deploy.split('permissions:', 1)[0]
        self.assertNotIn('tags:', trigger)
        self.assertIn('branches: [main]', trigger)
        self.assertNotIn('pull_request:', trigger)
        self.assertNotIn('schedule:', trigger)
        self.assertIn("github.ref == 'refs/heads/main'", deploy)
        self.assertIn("github.event_name == 'push'", deploy)
        self.assertIn("inputs.operation == 'deploy'", deploy)
        self.assertNotIn('workflow_run:', trigger)
        self.assertIn('cancel-in-progress: false', deploy)
        self.assertNotIn('cancel-in-progress: true', deploy)
        self.assertIn('needs: release_checks', deploy)
        self.assertEqual(deploy.count('run: python3 -B scripts/require-release-ci.py'), 2)
        self.assertNotIn('docker system prune', deploy)
        self.assertNotIn('docker builder prune', deploy)
        ci = (ROOT / '.github/workflows/ziwei-test.yml').read_text()
        self.assertIn('branches: [main, integration/ziwei-stripe-test]', ci)
        self.assertIn('test_release_gate.py', ci)


if __name__ == '__main__':
    unittest.main()
