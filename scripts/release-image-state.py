"""Bounded local-image rollback helper for the current reviewed release workflow.

Only application images are changed. No database restore, volume deletion, image
pull, credential operation, or old-workflow checkout. Invoke only through the
current trusted deployment workflow once its integration is reviewed.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

APP = Path('/opt/ai-engineer-portal')
STATE = Path('/opt/ai-engineer-portal-release-state')  # Outside git-clean scope.
SERVICES = ('backend', 'frontend')
DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
HEALTH_TIMEOUT_SECONDS = 300
FIELDS = {'version', 'candidate_sha', 'previous_sha', 'compose_sha256', 'images'}


# Output is selected only from these literals, never exception text or paths.
STAGES = frozenset({
    'candidate_compatibility', 'compose_read', 'state_directory', 'state_lock',
    'state_read', 'previous_commit', 'container_inspection', 'local_image_check',
    'record', 'prepare', 'rollback', 'operation',
})
REASONS = frozenset({
    'command_failed', 'unsafe_path', 'invalid_state', 'unsafe_state_permissions',
    'unsafe_state_path', 'invalid_candidate', 'oversized_state',
    'invalid_container_image', 'invalid_image', 'image_unavailable',
    'previous_service_not_healthy', 'rollback_health_failed',
    'candidate_compose_incompatible', 'git_dubious_ownership',
    'git_not_repository', 'git_permission_denied', 'git_command_failed',
})


@contextmanager
def diagnostic_stage(stage):
    """Annotate, but never replace, exceptions: existing catch behavior is intact."""
    try:
        yield
    except Exception as exc:
        if not hasattr(exc, '_release_stage'):
            exc._release_stage = stage if stage in STAGES else 'operation'
        raise


def failure_category(exc):
    if isinstance(exc, PermissionError):
        return 'permission_denied'
    if isinstance(exc, FileNotFoundError):
        return 'not_found'
    if isinstance(exc, FileExistsError):
        return 'already_exists'
    if isinstance(exc, BlockingIOError):
        return 'lock_unavailable'
    if isinstance(exc, subprocess.TimeoutExpired):
        return 'command_timeout'
    if isinstance(exc, json.JSONDecodeError):
        return 'invalid_json'
    if type(exc) is ValueError and len(exc.args) == 1:
        reason = exc.args[0]
        if type(reason) is str and reason in REASONS:
            return reason
    if isinstance(exc, OSError):
        return 'filesystem_error'
    return 'operation_failed'


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}', value) is not None


def valid_image(value):
    return isinstance(value, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value) is not None


def git_failure_category(stderr):
    """Diagnostic hints only: stderr is never printed and never relaxes a guard."""
    if not isinstance(stderr, str):
        return 'git_command_failed'
    # LANG is fixed to C.UTF-8. Inspect a bounded prefix; never include it in output.
    lines = stderr[:4096].splitlines()
    if any(line.startswith('fatal: detected dubious ownership in repository at ')
           for line in lines):
        return 'git_dubious_ownership'
    if any(line.startswith('fatal: not a git repository') for line in lines):
        return 'git_not_repository'
    if any(line.startswith(('fatal: ', 'error: ')) and line.endswith(': Permission denied')
           for line in lines):
        return 'git_permission_denied'
    return 'git_command_failed'


def command(args, timeout=30):
    # Only the fixed revision read gets diagnostic stderr. Docker is unchanged.
    git_revision = args == ['git', '--no-optional-locks', '-C', str(APP), 'rev-parse', 'HEAD']
    result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE if git_revision else subprocess.DEVNULL,
                            text=True, timeout=timeout,
                            check=False, env=ENV)
    if result.returncode:
        raise ValueError(git_failure_category(result.stderr) if git_revision else 'command_failed')
    return result.stdout.strip()


@diagnostic_stage('compose_read')
def compose_hash():
    path = APP / 'infra/docker-compose.prod.yml'
    if APP.resolve() != APP or path.resolve() != path:
        raise ValueError('unsafe_path')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_state(data, candidate_sha, expected_compose_hash):
    if type(data) is not dict or set(data) != FIELDS:
        raise ValueError('invalid_state')
    if (type(data['version']) is not int or data['version'] != 1
            or not valid_sha(candidate_sha) or data['candidate_sha'] != candidate_sha
            or not valid_sha(data['previous_sha'])
            or data['compose_sha256'] != expected_compose_hash
            or not re.fullmatch(r'[0-9a-f]{64}', expected_compose_hash)):
        raise ValueError('invalid_state')
    images = data['images']
    if type(images) is not dict or set(images) != set(SERVICES):
        raise ValueError('invalid_state')
    if not all(valid_image(images[service]) for service in SERVICES):
        raise ValueError('invalid_state')


def check_private(info, directory=False):
    if (info.st_uid != os.geteuid() or info.st_mode & 0o077
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError('unsafe_state_permissions')


@diagnostic_stage('state_directory')
def state_directory(create=False):
    if STATE.parent.resolve() != STATE.parent:
        raise ValueError('unsafe_state_path')
    if create:
        STATE.mkdir(mode=0o700, exist_ok=True)
    check_private(STATE.lstat(), directory=True)
    return STATE


@contextmanager
def operation_lock(create=False):
    with diagnostic_stage('state_lock'):
        directory = state_directory(create=create)
        fd = os.open(directory / '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+') as stream:
            check_private(os.fstat(stream.fileno()))
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@diagnostic_stage('state_read')
def read_state(candidate_sha):
    if not valid_sha(candidate_sha):
        raise ValueError('invalid_candidate')
    path = state_directory() / (candidate_sha + '.json')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r') as stream:
        check_private(os.fstat(stream.fileno()))
        payload = stream.read(4097)
    if len(payload) > 4096:
        raise ValueError('oversized_state')
    data = json.loads(payload)
    validate_state(data, candidate_sha, compose_hash())
    return data


@diagnostic_stage('container_inspection')
def inspect_container(service, timeout=30):
    raw = command(DOCKER + ['inspect', '--format',
                            '{{json .Image}} {{json .State.Status}} {{json .State.Health.Status}}',
                            'infra-' + service + '-1'], timeout=timeout)
    image, status, health = [json.loads(item) for item in raw.split()]
    if not valid_image(image):
        raise ValueError('invalid_container_image')
    return image, status, health


@diagnostic_stage('local_image_check')
def require_local_image(image):
    if not valid_image(image):
        raise ValueError('invalid_image')
    if command(DOCKER + ['image', 'inspect', '--format', '{{.Id}}', image]) != image:
        raise ValueError('image_unavailable')


@diagnostic_stage('record')
def record(candidate_sha):
    if not valid_sha(candidate_sha):
        raise ValueError('invalid_candidate')
    with diagnostic_stage('previous_commit'):
        previous = command(['git', '--no-optional-locks', '-C', str(APP), 'rev-parse', 'HEAD'])
    images = {}
    for service in SERVICES:
        image, status, health = inspect_container(service)
        if status != 'running' or health != 'healthy':
            raise ValueError('previous_service_not_healthy')
        require_local_image(image)
        images[service] = image
    data = dict(version=1, candidate_sha=candidate_sha, previous_sha=previous,
                compose_sha256=compose_hash(), images=images)
    validate_state(data, candidate_sha, compose_hash())
    directory = state_directory(create=True)
    path = directory / (candidate_sha + '.json')
    # Exclusive creation never replaces prior evidence. Partial writes fail closed
    # on subsequent parsing; an operator must investigate rather than overwrite.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    return data


@diagnostic_stage('prepare')
def prepare(candidate_sha):
    """Reuse a valid original rollback point on rerun; never replace it."""
    try:
        data = read_state(candidate_sha)
    except FileNotFoundError:
        return record(candidate_sha)
    for service in SERVICES:
        require_local_image(data['images'][service])
    return data


@diagnostic_stage('rollback')
def rollback(candidate_sha):
    data = read_state(candidate_sha)
    # Validate ALL inputs and local image availability before changing either tag.
    for service in SERVICES:
        require_local_image(data['images'][service])
    for service in SERVICES:
        command(DOCKER + ['tag', data['images'][service], 'infra-' + service + ':latest'])
    command(DOCKER + ['compose', '--project-name', 'infra',
                      '--project-directory', str(APP / 'infra'),
                      '--env-file', str(APP / 'infra/.env.production'),
                      '-f', str(APP / 'infra/docker-compose.prod.yml'),
                      'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                      '--force-recreate', 'backend', 'frontend'], timeout=120)
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        healthy = True
        for service in SERVICES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('rollback_health_failed')
            image, status, health = inspect_container(service, timeout=min(10, remaining))
            healthy = healthy and (image == data['images'][service]
                                   and status == 'running' and health == 'healthy')
        if healthy:
            return
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(5, remaining))
    raise ValueError('rollback_health_failed')


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] not in ('record', 'prepare', 'rollback') or not valid_sha(args[1]):
        print('Release image state: invalid request')
        return 1
    try:
        if args[0] == 'prepare':
            with diagnostic_stage('candidate_compatibility'):
                expected = os.environ.get('EXPECTED_COMPOSE_SHA256', '')
                if not re.fullmatch(r'[0-9a-f]{64}', expected) or compose_hash() != expected:
                    raise ValueError('candidate_compose_incompatible')
        with operation_lock(create=args[0] in ('record', 'prepare')):
            {'record': record, 'prepare': prepare, 'rollback': rollback}[args[0]](args[1])
    except Exception as exc:
        stage = getattr(exc, '_release_stage', 'operation')
        if type(stage) is not str or stage not in STAGES:
            stage = 'operation'
        print('Release image state: operation failed stage=' + stage
              + ' category=' + failure_category(exc))
        return 1
    print('Release image state: operation completed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
