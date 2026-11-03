"""Exercise deployment shell fragments only in temporary repos with mocked services.

Run without application dependencies: python -m unittest discover -s backend/tests
-p test_deploy_safety.py -v
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/deploy.yml'


class DeploySafetyTests(unittest.TestCase):
    def test_cleanup_preserves_backups_even_with_old_ignore_rules(self):
        for source in (ROOT / 'scripts/deploy-on-server.sh', WORKFLOW):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                subprocess.run(['git', 'init', '-q', directory], check=True)
                # Deployment cleans BEFORE updating the checkout's .gitignore.
                (repo / '.gitignore').write_text('infra/.env.production\n')
                subprocess.run(['git', '-C', directory, 'add', '.gitignore'], check=True)
                (repo / 'backups/nested').mkdir(parents=True)
                dump = repo / 'backups/nested/portal_fixture.dump'
                dump.write_bytes(b'fixture database backup')
                (repo / 'stale.txt').write_text('remove me')
                lines = [line.strip() for line in source.read_text().splitlines()
                         if line.strip().startswith('git clean ')]
                self.assertEqual(len(lines), 1)
                # Execute only the actual git-clean invocation, never the deploy script.
                command = shlex.split(lines[0].split('2>/dev/null')[0])
                subprocess.run(command, cwd=repo, check=True, capture_output=True)
                self.assertTrue(dump.exists(), 'deployment deleted the backup')
                self.assertEqual(dump.read_bytes(), b'fixture database backup')
                self.assertFalse((repo / 'stale.txt').exists())

    def test_backups_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', directory], check=True)
            shutil.copyfile(ROOT / '.gitignore', repo / '.gitignore')
            result = subprocess.run(['git', 'check-ignore', 'backups/portal_fixture.dump'],
                                    cwd=repo, capture_output=True)
            self.assertEqual(result.returncode, 0)

    def run_health(self, success_at=0, restarting=False):
        # Only the health SSH body is executed. Docker and sleep are PATH mocks;
        # no deploy, network, database, swap, or host paths are touched.
        step = WORKFLOW.read_text().split('      - name: Verify health via SSH\n', 1)[1]
        script = textwrap.dedent(step.split('          script: |\n', 1)[1].split('\n      - name:', 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / 'docker'
            docker.write_text('''#!/bin/bash
set -eu
if [ "$1" = exec ]; then
  n=$(cat "$PROBE_COUNT")
  n=$((n + 1))
  echo "$n" > "$PROBE_COUNT"
  [ "$SUCCESS_AT" -gt 0 ] && [ "$n" -ge "$SUCCESS_AT" ]
elif [ "$1" = compose ]; then
  echo "$CONTAINER_STATUS"
else
  exit 99
fi
''')
            sleep = root / 'sleep'
            sleep.write_text('#!/bin/bash\nexit 0\n')
            docker.chmod(0o755)
            sleep.chmod(0o755)
            count = root / 'count'
            count.write_text('0')
            env = {**os.environ, 'PATH': f'{root}:/usr/bin:/bin',
                   'PROBE_COUNT': str(count), 'SUCCESS_AT': str(success_at),
                   'CONTAINER_STATUS': 'Restarting' if restarting else 'Up 1 minute'}
            result = subprocess.run(['bash', '-c', script], env=env,
                                    capture_output=True, text=True, timeout=5)
            return result, int(count.read_text())

    def test_exhausted_health_probes_fail_even_when_no_container_restarts(self):
        result, probes = self.run_health()
        self.assertEqual(probes, 5)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('All containers healthy', result.stdout)

    def test_health_success_stops_retries(self):
        for attempt in (1, 3, 5):
            with self.subTest(attempt=attempt):
                result, probes = self.run_health(success_at=attempt)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(probes, attempt)
                self.assertIn('All containers healthy', result.stdout)

    def test_restarting_containers_still_fail_after_successful_probe(self):
        result, probes = self.run_health(success_at=1, restarting=True)
        self.assertEqual(probes, 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('All containers healthy', result.stdout)


if __name__ == '__main__':
    unittest.main()
