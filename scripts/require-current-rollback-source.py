"""Read-only guard: rollback executes only the current main workflow revision."""
import json
import os
import re
import sys
import urllib.request

REPOSITORY = 'stinger0962/AIEngineerPortal'
URL = 'https://api.github.com/repos/' + REPOSITORY + '/branches/main'


def fetch_main_sha(token):
    request = urllib.request.Request(URL, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)['commit']['sha']


def main():
    sha = os.environ.get('GITHUB_SHA', '')
    token = os.environ.get('GH_TOKEN', '')
    if (os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or os.environ.get('GITHUB_REPOSITORY') != REPOSITORY
            or not re.fullmatch(r'[0-9a-f]{40}', sha) or not token):
        print('Rollback source: invalid context')
        return 1
    try:
        if fetch_main_sha(token) != sha:
            print('Rollback source: stale workflow revision')
            return 1
    except Exception:
        print('Rollback source: verification unavailable')
        return 1
    print('Rollback source: current main verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
