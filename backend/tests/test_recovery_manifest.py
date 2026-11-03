"""Synthetic evidence only. These tests never make or restore a real backup."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('manifest', ROOT / 'scripts/validate-recovery-manifest.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SOURCE = 'a' * 40
DUMP = 'b' * 64
SENTINEL = 'secret-must-not-appear'


def fixture():
    return dict(schema_version=1, source_sha=SOURCE, dump_sha256=DUMP,
                dump_bytes=4096, postgres_major=16,
                dump_completed_at='2026-11-03T10:00:00Z',
                restore_started_at='2026-11-03T10:01:00Z',
                restore_completed_at='2026-11-03T10:02:00Z',
                restore_exit_code=0, validation_exit_code=0, restored_tables=5,
                isolation_network='none', production_volume_mounted=False)


class RecoveryManifestTests(unittest.TestCase):
    def validate(self, document, **context):
        args = dict(expected_source_sha=SOURCE, expected_dump_sha256=DUMP,
                    expected_table_count=5, max_age_seconds=3600,
                    now=datetime(2026, 11, 3, 10, 3, tzinfo=timezone.utc))
        args.update(context)
        result = MODULE.validate_manifest(document, **args)
        self.assertNotIn(SENTINEL, repr(result))
        return result

    def test_complete_synthetic_record_is_schema_valid_only(self):
        self.assertEqual(self.validate(fixture()), ())

    def test_unknown_secret_fields_and_missing_evidence_are_rejected(self):
        document = fixture()
        document[SENTINEL] = SENTINEL
        self.assertEqual(self.validate(document), ('unknown_fields',))
        for field in MODULE.FIELDS:
            document = fixture()
            del document[field]
            self.assertEqual(self.validate(document), ('missing_fields',))
        self.assertEqual(self.validate(None), ('invalid_document',))

    def test_expected_hashes_must_match_independent_context(self):
        for field, value, error in [('source_sha', 'c' * 40, 'source_mismatch'),
                                    ('dump_sha256', 'c' * 64, 'dump_mismatch'),
                                    ('dump_sha256', SENTINEL, 'dump_mismatch')]:
            document = fixture()
            document[field] = value
            self.assertIn(error, self.validate(document))

    def test_failed_incomplete_or_boolean_results_are_rejected(self):
        for field in ('restore_exit_code', 'validation_exit_code'):
            for value in (1, None, False, '0'):
                document = fixture()
                document[field] = value
                self.assertIn('restore_or_validation_failed', self.validate(document))
        for value in (0, 4, True, '5'):
            document = fixture()
            document['restored_tables'] = value
            self.assertIn('table_count_mismatch', self.validate(document))

    def test_unsafe_isolation_is_rejected(self):
        for field, value in [('isolation_network', 'bridge'),
                             ('production_volume_mounted', True),
                             ('production_volume_mounted', 0)]:
            document = fixture()
            document[field] = value
            self.assertIn('unsafe_isolation', self.validate(document))

    def test_timestamp_format_order_future_and_freshness_are_enforced(self):
        for value in ('2026-11-03', '2026-11-03T10:02:00', '2026-02-30T00:00:00Z', SENTINEL):
            document = fixture()
            document['restore_completed_at'] = value
            self.assertIn('invalid_timestamp', self.validate(document))
        document = fixture()
        document['restore_completed_at'] = '2026-11-03T10:04:00Z'
        self.assertIn('invalid_time_order', self.validate(document))
        document = fixture()
        document['restore_started_at'] = '2026-11-03T09:59:00Z'
        self.assertIn('invalid_time_order', self.validate(document))
        self.assertIn('stale_evidence', self.validate(fixture(), max_age_seconds=60))

    def test_invalid_context_cannot_self_authorize_a_manifest(self):
        for context in ({'expected_source_sha': SENTINEL}, {'expected_dump_sha256': ''},
                        {'expected_table_count': 0}, {'max_age_seconds': True},
                        {'now': datetime(2026, 11, 3)}):
            self.assertEqual(self.validate(fixture(), **context), ('invalid_validation_context',))

    def test_invalid_versions_and_sizes_are_rejected(self):
        for field, value, error in [('schema_version', True, 'unsupported_schema'),
                                    ('postgres_major', 15, 'unsupported_database_version'),
                                    ('dump_bytes', 0, 'invalid_dump_size'),
                                    ('dump_bytes', True, 'invalid_dump_size')]:
            document = fixture()
            document[field] = value
            self.assertIn(error, self.validate(document))


if __name__ == '__main__':
    unittest.main()
