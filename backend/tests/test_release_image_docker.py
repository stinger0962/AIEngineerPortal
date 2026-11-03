"""Opt-in rehearsal on disposable GitHub CI Docker only. Never contacts production."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('image_state', ROOT / 'scripts/release-image-state.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']


@unittest.skipUnless(os.environ.get('RUN_CODE_ROLLBACK_DOCKER_TEST') == '1',
                     'Requires explicit isolated CI opt-in')
class DockerRollbackRehearsal(unittest.TestCase):
    def run_command(self, args, **kwargs):
        return subprocess.run(args, check=True, text=True, capture_output=True,
                              timeout=120, **kwargs).stdout.strip()

    def docker(self, *args):
        return self.run_command(DOCKER + list(args))

    def exists(self, args):
        return subprocess.run(DOCKER + args, capture_output=True, timeout=20).returncode == 0

    def test_real_local_image_rollback_preserves_fixture_volume(self):
        self.assertEqual(os.environ.get('GITHUB_ACTIONS'), 'true')
        self.assertEqual(os.environ.get('GITHUB_REPOSITORY'), 'stinger0962/AIEngineerPortal')
        # Never replace preexisting resources. These fixed names match the helper.
        for name in ('infra-backend-1', 'infra-frontend-1'):
            self.assertFalse(self.exists(['container', 'inspect', name]))
        self.assertFalse(self.exists(['volume', 'inspect', 'infra_rollback_fixture']))
        tags = ('infra-backend:latest', 'infra-frontend:latest',
                'rollback-ci-fixture:old', 'rollback-ci-fixture:new')
        for tag in tags:
            self.assertFalse(self.exists(['image', 'inspect', tag]))
        # Already pulled by this job's PostgreSQL service; no registry/network build.
        self.assertTrue(self.exists(['image', 'inspect', 'postgres:16-alpine']))
        self.docker('compose', 'version')
        with tempfile.TemporaryDirectory(prefix='rollback-ci-') as directory:
            root = Path(directory)
            app = root / 'app'
            infra = app / 'infra'
            infra.mkdir(parents=True)
            compose_file = infra / 'docker-compose.prod.yml'
            compose_file.write_text('''services:
  backend:
    image: infra-backend:latest
    volumes:
      - rollback_fixture:/fixture
  frontend:
    image: infra-frontend:latest
    volumes:
      - rollback_fixture:/fixture
volumes:
  rollback_fixture:
''')
            (infra / '.env.production').write_text('')
            (root / 'Dockerfile').write_text('''FROM postgres:16-alpine
ENTRYPOINT []
CMD ["sh", "-c", "sleep 3600"]
HEALTHCHECK --interval=1s --timeout=1s --retries=10 CMD true
ARG REVISION
LABEL rollback.ci.fixture=$REVISION
''')
            self.run_command(['git', 'init', '-q', str(app)])
            self.run_command(['git', '-C', str(app), 'add', '.'])
            self.run_command(['git', '-C', str(app), '-c', 'user.name=CI Fixture',
                              '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'])
            compose = DOCKER + ['compose', '--project-name', 'infra',
                                '--project-directory', str(infra),
                                '--env-file', str(infra / '.env.production'),
                                '-f', str(compose_file)]
            created = False
            built = False
            try:
                for revision in ('old', 'new'):
                    self.docker('build', '--pull=false', '--network', 'none',
                                '--build-arg', 'REVISION=' + revision,
                                '-t', 'rollback-ci-fixture:' + revision, str(root))
                    built = True
                old = self.docker('image', 'inspect', '--format', '{{.Id}}', 'rollback-ci-fixture:old')
                new = self.docker('image', 'inspect', '--format', '{{.Id}}', 'rollback-ci-fixture:new')
                self.assertNotEqual(old, new)
                for service in MODULE.SERVICES:
                    self.docker('tag', old, 'infra-' + service + ':latest')
                created = True
                self.run_command(compose + ['up', '-d', '--no-build', '--pull', 'never'])
                with patch.object(MODULE, 'APP', app), patch.object(MODULE, 'STATE', root / 'state'):
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        if all(MODULE.inspect_container(s)[1:] == ('running', 'healthy')
                               for s in MODULE.SERVICES):
                            break
                        time.sleep(1)
                    self.assertTrue(all(MODULE.inspect_container(s)[1:] == ('running', 'healthy')
                                        for s in MODULE.SERVICES))
                    candidate = 'a' * 40
                    self.assertEqual(MODULE.main(['record', candidate]), 0)
                    self.docker('exec', 'infra-backend-1', 'sh', '-c',
                                'printf rollback-fixture > /fixture/sentinel')
                    for service in MODULE.SERVICES:
                        self.docker('tag', new, 'infra-' + service + ':latest')
                    self.run_command(compose + ['up', '-d', '--no-deps', '--no-build',
                                               '--pull', 'never', '--force-recreate', 'backend', 'frontend'])
                    self.assertTrue(all(MODULE.inspect_container(s)[0] == new for s in MODULE.SERVICES))
                    self.assertEqual(MODULE.main(['rollback', candidate]), 0)
                    self.assertTrue(all(MODULE.inspect_container(s) == (old, 'running', 'healthy')
                                        for s in MODULE.SERVICES))
                    self.assertEqual(self.docker('exec', 'infra-backend-1', 'cat', '/fixture/sentinel'),
                                     'rollback-fixture')
            finally:
                # Only resources created by this isolated fixture, never production.
                if created:
                    self.run_command(compose + ['down', '--volumes'])
                if built:
                    for tag in tags:
                        if self.exists(['image', 'inspect', tag]):
                            self.docker('image', 'rm', tag)


if __name__ == '__main__':
    unittest.main()
