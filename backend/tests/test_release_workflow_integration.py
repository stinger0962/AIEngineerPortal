"""Workflow integration tests are static and mocked; never contact production."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('renderer', ROOT / 'scripts/render-release-helper.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = 'a' * 40


class ReleaseWorkflowIntegrationTests(unittest.TestCase):
    def test_rendered_helper_passes_bash_syntax_without_execution(self):
        source = (ROOT / 'scripts/release-image-state.py').read_text()
        for action in ('prepare', 'rollback'):
            output = MODULE.render(action, SHA, source)
            self.assertIn(source.rstrip(), output)
            self.assertIn('python3 -B - ' + action + ' ' + SHA, output)
            result = subprocess.run(['bash', '-n'], input=output, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)

    def test_arbitrary_action_sha_and_delimiter_are_rejected(self):
        for action, sha, source in [('pull', SHA, ''), ('rollback', '$(command)', ''),
                                    ('prepare', SHA + '\n', ''),
                                    ('prepare', SHA, MODULE.DELIMITER)]:
            with self.assertRaises(ValueError):
                MODULE.render(action, sha, source)

    def test_rollback_requires_main_before_rendering(self):
        with patch.dict(os.environ, {'RELEASE_ACTION': 'rollback', 'RELEASE_SHA': SHA,
                                    'GITHUB_REF': 'refs/heads/feature'}, clear=True), \
             contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(MODULE.main(), 1)
        self.assertEqual(output.getvalue(), '')

    def test_forward_capture_precedes_mutation_and_does_not_overwrite_state(self):
        text = (ROOT / '.github/workflows/deploy.yml').read_text()
        deploy = text.split('  deploy:\n', 1)[1].split('  rollback:\n', 1)[0]
        self.assertLess(deploy.index('Capture previous application images'),
                        deploy.index('Deploy on droplet'))
        self.assertIn('RELEASE_ACTION: prepare', deploy)
        self.assertIn('RELEASE_SHA: ${{ github.sha }}', deploy)
        self.assertNotIn('backup-db.sh', deploy)
        self.assertNotIn('production-preflight.sh', deploy)

    def test_rollback_uses_current_main_trust_and_no_forward_mutations(self):
        text = (ROOT / '.github/workflows/deploy.yml').read_text()
        rollback = text.split('  rollback:\n', 1)[1]
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.operation == 'rollback'", rollback)
        self.assertIn('test "$GITHUB_REF" = refs/heads/main', rollback)
        self.assertIn('RELEASE_ACTION: rollback', rollback)
        self.assertIn('RELEASE_SHA: ${{ inputs.rollback_release_sha }}', rollback)
        self.assertIn('fingerprint: SHA256:5l+l4ylrZutSMsq0T8rtMv5jF6cDPm6XtcnbwWWNSX4', rollback)
        self.assertIn('run: python3 -B scripts/public-smoke.py', rollback)
        for forbidden in ('require-release-ci.py', 'docker/build-push-action',
                          'upsert_env', 'docker login', 'git checkout', 'pg_restore'):
            self.assertNotIn(forbidden, rollback)
        trigger = text.split('concurrency:', 1)[0]
        self.assertNotIn('branches:', trigger)
        self.assertNotIn('workflow_run:', trigger)
        self.assertIn('group: production-release', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertNotIn('continue-on-error', text)


if __name__ == '__main__':
    unittest.main()
