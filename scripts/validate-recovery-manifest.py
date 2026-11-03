"""Offline manifest validation only; never proof that a backup or restore occurred.

No filesystem, subprocess, network, logging, deployment or credential operations.
A future trusted runner must independently bind evidence to real operation results.
"""
from datetime import datetime, timezone
import re

FIELDS = frozenset({
    'schema_version', 'source_sha', 'dump_sha256', 'dump_bytes', 'postgres_major',
    'dump_completed_at', 'restore_started_at', 'restore_completed_at',
    'restore_exit_code', 'validation_exit_code', 'restored_tables',
    'isolation_network', 'production_volume_mounted',
})
TIMES = ('dump_completed_at', 'restore_started_at', 'restore_completed_at')


def is_int(value):
    return type(value) is int  # bool is not evidence of an integer result.


def digest(value, length):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def parse_utc(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise ValueError
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def validate_manifest(document, *, expected_source_sha, expected_dump_sha256,
                      expected_table_count, max_age_seconds, now):
    """Return fixed error codes. Empty tuple means schema/consistency valid ONLY.

    Expected values and time policy must come from an independent trusted caller,
    never be copied from the untrusted manifest to make it pass.
    """
    if (not digest(expected_source_sha, 40) or not digest(expected_dump_sha256, 64)
            or not is_int(expected_table_count) or expected_table_count <= 0
            or not is_int(max_age_seconds) or max_age_seconds <= 0
            or not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        return ('invalid_validation_context',)
    if type(document) is not dict:
        return ('invalid_document',)
    errors = set()
    if set(document) - FIELDS:
        errors.add('unknown_fields')
    if FIELDS - set(document):
        errors.add('missing_fields')
    if errors:
        return tuple(sorted(errors))
    if not is_int(document['schema_version']) or document['schema_version'] != 1:
        errors.add('unsupported_schema')
    if not digest(document['source_sha'], 40) or document['source_sha'] != expected_source_sha:
        errors.add('source_mismatch')
    if not digest(document['dump_sha256'], 64) or document['dump_sha256'] != expected_dump_sha256:
        errors.add('dump_mismatch')
    if not is_int(document['dump_bytes']) or document['dump_bytes'] <= 0:
        errors.add('invalid_dump_size')
    if not is_int(document['postgres_major']) or document['postgres_major'] != 16:
        errors.add('unsupported_database_version')
    if (not is_int(document['restore_exit_code']) or document['restore_exit_code'] != 0
            or not is_int(document['validation_exit_code']) or document['validation_exit_code'] != 0):
        errors.add('restore_or_validation_failed')
    if not is_int(document['restored_tables']) or document['restored_tables'] != expected_table_count:
        errors.add('table_count_mismatch')
    if (document['isolation_network'] != 'none'
            or document['production_volume_mounted'] is not False):
        errors.add('unsafe_isolation')
    try:
        created, started, completed = [parse_utc(document[key]) for key in TIMES]
        if not created <= started <= completed <= now:
            errors.add('invalid_time_order')
        if (now - created).total_seconds() > max_age_seconds:
            errors.add('stale_evidence')
    except (ValueError, TypeError, OverflowError):
        errors.add('invalid_timestamp')
    return tuple(sorted(errors))
