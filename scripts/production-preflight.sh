#!/usr/bin/env bash
set +x
set -eu
# Fixed, read-only inspection. Never source .env or import application startup code.
# Python runs from stdin with bytecode disabled; nothing is installed on the host.
python3 -B - <<'PY'
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

APP = Path('/opt/ai-engineer-portal')
SERVICES = ('backend', 'frontend', 'postgres', 'redis', 'caddy')
HEX = re.compile(r'[0-9a-f]{40}')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')
# This program prints only allowlisted booleans and presence indicators.
FLAGS_PROGRAM = '''import json, os
flags = {}
for key in ('STRIPE_TEST_ENABLED', 'ZIWEI_REQUIRE_CREDITS'):
    value = os.environ.get(key)
    flags[key] = ('unset' if value is None else value.lower() if value.lower() in ('true', 'false') else 'non_boolean')
for key in ('STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET'):
    flags[key] = 'present' if os.environ.get(key) else 'absent'
print(json.dumps(flags))
'''


def command(args):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, timeout=10, check=False)
    if result.returncode:
        raise RuntimeError('inspection command failed')
    return result.stdout.strip()


def inspect_service(service):
    name = f'infra-{service}-1'
    # Selected fields only; never request the container environment or health logs.
    raw = command(['docker', 'inspect', '--format',
                   '{{json .State.Status}} {{if .State.Health}}{{json .State.Health.Status}}{{else}}"none"{{end}} {{json .Image}}', name])
    status, health, image_id = raw.split()
    status, health, image_id = map(json.loads, (status, health, image_id))
    if status not in ('created', 'running', 'paused', 'restarting', 'removing', 'exited', 'dead'):
        raise ValueError('unexpected status')
    if health not in ('none', 'starting', 'healthy', 'unhealthy') or not DIGEST.fullmatch(image_id):
        raise ValueError('unexpected metadata')
    repos = json.loads(command(['docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', image_id]))
    # Emit digest hashes only; repository names may be private or arbitrary strings.
    digests = sorted({entry.rsplit('@', 1)[-1] for entry in (repos or [])
                      if isinstance(entry, str) and DIGEST.fullmatch(entry.rsplit('@', 1)[-1])})
    return dict(status=status, health=health, image_id=image_id, registry_digests=digests)


class BackupInspectionError(Exception):
    """Only fixed, non-sensitive status labels may reach the report."""
    ALLOWED = {'directory_missing', 'permission_denied', 'symlink_rejected',
               'invalid_directory', 'metadata_unavailable'}

    def __init__(self, code):
        self.code = code if code in self.ALLOWED else 'metadata_unavailable'


def inspect_backups():
    directory = APP / 'backups'
    try:
        mode = directory.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise BackupInspectionError('symlink_rejected')
        if not stat.S_ISDIR(mode):
            raise BackupInspectionError('invalid_directory')
        entries = os.scandir(directory)
    except FileNotFoundError:
        raise BackupInspectionError('directory_missing') from None
    except PermissionError:
        raise BackupInspectionError('permission_denied') from None
    except NotADirectoryError:
        raise BackupInspectionError('invalid_directory') from None
    except OSError:
        raise BackupInspectionError('metadata_unavailable') from None
    metadata = []
    try:
        with entries:
            for entry in entries:
                if entry.name.startswith('portal_') and entry.name.endswith('.dump') and entry.is_file(follow_symlinks=False):
                    info = entry.stat(follow_symlinks=False)
                    metadata.append((info.st_mtime, info.st_size))
        latest = max(metadata) if metadata else None
        return dict(count=len(metadata), latest_utc=datetime.datetime.fromtimestamp(
            latest[0], datetime.timezone.utc).isoformat() if latest else None,
            latest_bytes=latest[1] if latest else None,
            restore_verified=False)
    except PermissionError:
        raise BackupInspectionError('permission_denied') from None
    except Exception:
        raise BackupInspectionError('metadata_unavailable') from None


def inspect_flags():
    flags = json.loads(command(['docker', 'exec', 'infra-backend-1', 'python', '-B', '-c', FLAGS_PROGRAM]))
    expected = {'STRIPE_TEST_ENABLED': {'true', 'false', 'unset', 'non_boolean'},
                'ZIWEI_REQUIRE_CREDITS': {'true', 'false', 'unset', 'non_boolean'},
                'STRIPE_SECRET_KEY': {'present', 'absent'},
                'STRIPE_WEBHOOK_SECRET': {'present', 'absent'}}
    if set(flags) != set(expected) or any(flags[k] not in values for k, values in expected.items()):
        raise ValueError('unexpected flags')
    return flags


def main():
    report = {}
    failed = False
    def capture(key, operation):
        nonlocal failed
        try:
            report[key] = operation()
        except BackupInspectionError as error:
            report[key] = {'error': error.code, 'restore_verified': False}
            failed = True
        except Exception:
            # Do not echo command output, exception text, paths, or secret-bearing values.
            report[key] = {'error': 'unavailable'}
            failed = True
    def revision():
        value = command(['git', '--no-optional-locks', '-C', str(APP), 'rev-parse', 'HEAD'])
        if not HEX.fullmatch(value):
            raise ValueError('unexpected revision')
        return value
    def disk():
        total, used, free = shutil.disk_usage(APP)
        return dict(total_bytes=total, used_bytes=used, free_bytes=free)
    capture('deployed_revision', revision)
    for service in SERVICES:
        capture(service, lambda service=service: inspect_service(service))
    capture('disk', disk)
    capture('backups', inspect_backups)
    capture('payment_environment', inspect_flags)
    print(json.dumps(report, sort_keys=True))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
PY
