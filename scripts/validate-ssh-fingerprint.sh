#!/usr/bin/env bash
set +x
set -eu
# Validation checks syntax only. The operator must establish provenance independently.
if [[ ! ${HOST_FINGERPRINT:-} =~ ^SHA256:[A-Za-z0-9+/]{43}$ ]]; then
  echo 'A verified SHA256 SSH host fingerprint is required.' >&2
  exit 1
fi
