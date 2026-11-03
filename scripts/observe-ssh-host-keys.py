"""Unauthenticated, read-only observation; output is NOT trusted host-key material."""
import base64
import ipaddress
import json
import os
import re
import socket
import subprocess

# Portal Droplet address confirmed by the owner via its trusted console.
EXPECTED_IP = '146.190.124.162'
PORT = 22  # Same fixed default port as the existing SSH action.
KEY_TYPES = {'ssh-ed25519', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384',
             'ecdsa-sha2-nistp521', 'ssh-rsa'}


def capture(args, stdin=None):
    result = subprocess.run(args, input=stdin, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, timeout=15,
                            check=False)
    if result.returncode:
        raise ValueError('observation failed')
    return result.stdout


def observe():
    report = {'expected_ip_match': False, 'observed_public_keys': []}
    try:
        host = os.environ.get('VPS_HOST', '')
        # Reject lists, ports, options and shell syntax; no arbitrary target input.
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', host):
            raise ValueError('invalid target')
        addresses = {str(ipaddress.ip_address(item[4][0])) for item in
                     socket.getaddrinfo(host, PORT, type=socket.SOCK_STREAM)}
        report['expected_ip_match'] = addresses == {EXPECTED_IP}
        if not report['expected_ip_match']:
            raise ValueError('unexpected target')
        # Pin observation to the resolved, expected IP to avoid a second DNS lookup.
        # No private key, username, authentication, known_hosts or remote commands.
        output = capture(['ssh-keyscan', '-T', '5', '-p', str(PORT), '-t',
                          'ed25519,ecdsa,rsa', EXPECTED_IP])
        keys = set()
        for line in output.splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split()
            if len(fields) != 3 or fields[1] not in KEY_TYPES:
                raise ValueError('unexpected key output')
            key_type, encoded = fields[1:]
            base64.b64decode(encoded, validate=True)
            # Strip the target field before fingerprinting; do not log raw output.
            summary = capture(['ssh-keygen', '-l', '-E', 'sha256', '-f', '/dev/stdin'],
                              f'{key_type} {encoded}\n')
            match = re.fullmatch(r'\d+ (SHA256:[A-Za-z0-9+/]{43}) [^\n]*\n?', summary)
            if not match:
                raise ValueError('unexpected fingerprint output')
            keys.add((key_type, match[1]))
        if not keys:
            raise ValueError('no keys observed')
        report['observed_public_keys'] = [dict(type=kind, fingerprint=value)
                                          for kind, value in sorted(keys)]
    except Exception:
        # Exceptions and tool diagnostics can contain the secret destination.
        report['error'] = 'host_key_observation_unavailable'
        print(json.dumps(report, sort_keys=True))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(observe())
