"""Render reviewed helper source as an SSH script; never executes it locally."""
import hashlib
import os
from pathlib import Path
import re
import sys

DELIMITER = 'PY_PORTAL_IMAGE_STATE'


def render(action, sha, source, compose_sha256=None):
    if action not in ('prepare', 'prepare-auto', 'rollback') or not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('invalid request')
    if DELIMITER in source.splitlines():
        raise ValueError('invalid source delimiter')
    prefix = ''
    if action in ('prepare', 'prepare-auto'):
        if not isinstance(compose_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', compose_sha256):
            raise ValueError('invalid compose hash')
        prefix = 'EXPECTED_COMPOSE_SHA256=' + compose_sha256 + ' '
    return ('#!/usr/bin/env bash\nset +x\nset -eu\n'
            + prefix + "python3 -B - " + action + " " + sha + " <<'" + DELIMITER + "'\n"
            + source.rstrip() + '\n' + DELIMITER + '\n')


def main():
    try:
        action = os.environ.get('RELEASE_ACTION', '')
        if action == 'rollback' and os.environ.get('GITHUB_REF') != 'refs/heads/main':
            raise ValueError('rollback must use main')
        source = (Path(__file__).resolve().parent / 'release-image-state.py').read_text()
        compose_sha256 = None
        if action in ('prepare', 'prepare-auto'):
            compose = Path(__file__).resolve().parents[1] / 'infra/docker-compose.prod.yml'
            compose_sha256 = hashlib.sha256(compose.read_bytes()).hexdigest()
        output = render(action, os.environ.get('RELEASE_SHA', ''), source, compose_sha256)
    except Exception:
        print('Release helper rendering failed', file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
