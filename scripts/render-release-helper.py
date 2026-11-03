"""Render reviewed helper source as an SSH script; never executes it locally."""
import os
from pathlib import Path
import re
import sys

DELIMITER = 'PY_PORTAL_IMAGE_STATE'


def render(action, sha, source):
    if action not in ('prepare', 'rollback') or not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('invalid request')
    if DELIMITER in source.splitlines():
        raise ValueError('invalid source delimiter')
    return ('#!/usr/bin/env bash\nset +x\nset -eu\n'
            + "python3 -B - " + action + " " + sha + " <<'" + DELIMITER + "'\n"
            + source.rstrip() + '\n' + DELIMITER + '\n')


def main():
    try:
        action = os.environ.get('RELEASE_ACTION', '')
        if action == 'rollback' and os.environ.get('GITHUB_REF') != 'refs/heads/main':
            raise ValueError('rollback must use main')
        source = (Path(__file__).resolve().parent / 'release-image-state.py').read_text()
        output = render(action, os.environ.get('RELEASE_SHA', ''), source)
    except Exception:
        print('Release helper rendering failed', file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
