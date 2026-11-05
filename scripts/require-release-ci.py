"""Fail-closed release gate. Read-only GitHub API; never contacts production."""
import json
import os
import re
import time
import urllib.parse
import urllib.request

REPOSITORY = 'stinger0962/AIEngineerPortal'
WORKFLOW = '.github/workflows/ziwei-test.yml'
API = 'https://api.github.com/repos/' + REPOSITORY
ATTEMPTS = 60
DELAY_SECONDS = 15


def evaluate_runs(runs, sha):
    candidates = [run for run in runs if
                  run.get('head_sha') == sha and
                  run.get('head_branch') == 'main' and
                  run.get('event') == 'push' and
                  run.get('path') == WORKFLOW and
                  (run.get('head_repository') or {}).get('full_name') == REPOSITORY]
    if not candidates:
        return 'pending'
    latest = max(candidates, key=lambda run: run['id'])
    if latest.get('status') != 'completed':
        return 'pending'
    return 'success' if latest.get('conclusion') == 'success' else 'failed'


def request_json(path, token):
    request = urllib.request.Request(API + path, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def check(sha, token):
    # Refuse an older queued release after main has advanced.
    if request_json('/branches/main', token)['commit']['sha'] != sha:
        return 'stale'
    runs = []
    for page in range(1, 11):
        query = urllib.parse.urlencode({'head_sha': sha, 'event': 'push',
                                        'per_page': 100, 'page': page})
        batch = request_json('/actions/runs?' + query, token)['workflow_runs']
        runs.extend(batch)
        if len(batch) < 100:
            return evaluate_runs(runs, sha)
    return 'failed'  # Never make a decision from an incomplete result set.


def main():
    sha = os.environ.get('GITHUB_SHA', '')
    token = os.environ.get('GH_TOKEN', '')
    # Only a main push or an explicitly requested main deployment may proceed.
    # Re-running a production job is manual; CI completions never retry releases.
    event = os.environ.get('GITHUB_EVENT_NAME', '')
    if (event not in ('push', 'workflow_dispatch') or
            (event == 'push' and os.environ.get('GITHUB_RUN_ATTEMPT') != '1') or
            os.environ.get('GITHUB_REF') != 'refs/heads/main' or
            os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or
            not re.fullmatch(r'[0-9a-f]{40}', sha) or not token):
        print('Release gate: invalid context')
        return 1
    for attempt in range(ATTEMPTS):
        try:
            result = check(sha, token)
        except Exception:
            # API errors may contain headers or private response details.
            print('Release gate: verification unavailable')
            return 1
        if result == 'success':
            print('Release gate: exact main commit CI passed')
            return 0
        if result != 'pending':
            print('Release gate: commit or CI is not eligible')
            return 1
        if attempt + 1 < ATTEMPTS:
            time.sleep(DELAY_SECONDS)
    print('Release gate: timed out waiting for exact main commit CI')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
