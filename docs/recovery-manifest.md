# Recovery manifest preparation

This is an **offline schema and consistency validator**, not a backup generator,
restore runner, attestation verifier, deployment gate, or proof of recovery.
The fixtures are synthetic. No real backup, restore, off-host copy or production
change was performed by this work. An empty error tuple must never be presented
as `restore_verified: true` or release authorization.

## Contract

`scripts/validate-recovery-manifest.py` accepts only the documented flat record:
schema version 1; exact source commit; dump SHA256 and positive size; PostgreSQL
major 16; UTC dump/restore timestamps; zero restore and validation exit codes;
restored table count; network isolation `none`; and no mounted production volume.
It rejects extra/missing fields, mismatched independent expected values, failed
or incomplete results, unsafe isolation, invalid chronology and stale evidence.
Freshness policy and expected hash/table values must be supplied by a trusted
caller, not copied from the manifest. Errors are fixed codes and contain no
input values, paths, secrets, row contents or exception details.

The validator performs no I/O, subprocess execution, network calls or logging.
It is not wired to deployment and cannot enable a production trigger.
A fabricated self-reported record can satisfy a schema; independent provenance
and operation verification remain mandatory.

## Required future evidence producer

A separately reviewed runner must bind evidence to actual subprocess results,
a checksum of the completed archive, the source schema inventory captured from
the same backup snapshot, and a successful isolated PostgreSQL restore plus
integrity checks. Use the trusted database version/image, no production volume
mount, no published ports or external network, bounded resource/time limits,
and no application startup against production.

Create dumps atomically with restrictive permissions; preserve existing backups.
Never reuse the current backup script unchanged for this purpose: its age-based
deletion and size-only check do not establish recovery. Restore verification must
not print user records, credentials, raw command failures or dump contents.
Only an actual trusted producer can assert that operations happened; this module
checks the consistency of its record and is not that producer.

## Still unresolved

- Database size, memory capacity, expected source schema inventory and actual
  restore results have not been collected.
- Existing external backups and storage configuration remain unknown.
- Off-host destination, recipient/data authorization, cost, retention and access
  are unspecified. No bucket, credential, permission or paid service is created.
- Database dumps do not cover podcast audio, dubbed videos or all system config.
- A real release still needs fresh recovery evidence, explicit immutable rollback
  references, disk safeguards and baseline-test triage. Production triggers and
  payment settings are unchanged.

Do not activate automatic production deployment or delete earlier backups based
on these synthetic tests.
