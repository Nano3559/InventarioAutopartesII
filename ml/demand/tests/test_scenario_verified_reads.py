"""Regression tests for the bytes consumed by both frozen scenario runtimes."""
import hashlib
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from v2 import calendar2026_runtime as calendar, scenario_runtime as historical
from .test_scenario_runtime import request


RELEASES = (
    (calendar, calendar.REPORT / 'release.json', 'RELEASE_SHA', '4.0.0', 168),
    (historical, historical.RELEASE_PATH, 'EXPECTED_RELEASE_SHA256', '3.0.0', 504),
)


class VerifiedReadTests(TestCase):
    def setUp(self):
        for runtime, *_ in RELEASES:
            runtime.release.cache_clear()
            self.addCleanup(runtime.release.cache_clear)

    def assert_incompatible(self, action):
        with self.assertRaises(historical.ScenarioError) as error:
            action()
        self.assertEqual(error.exception.code, 'INCOMPATIBLE_ARTIFACT')

    def assert_single_verified_read(self, path, action):
        original_read_bytes = Path.read_bytes
        original_read_text = Path.read_text
        original = original_read_bytes(path)
        reads = []

        def read_bytes(file):
            if file != path:
                return original_read_bytes(file)
            reads.append('read_bytes')
            return original if len(reads) == 1 else b'{}'

        def read_text(file, *args, **kwargs):
            if file != path:
                return original_read_text(file, *args, **kwargs)
            reads.append('read_text')
            return '{}'

        with patch.object(Path, 'read_bytes', read_bytes), patch.object(Path, 'read_text', read_text):
            result = action()
        self.assertEqual(reads, ['read_bytes'])
        return result

    def test_release_and_snapshots_consume_verified_bytes_once(self):
        for runtime, manifest, _, version, count in RELEASES:
            metadata = json.loads(manifest.read_bytes())
            snapshot = runtime.ROOT / metadata['snapshots']
            for path in (manifest, snapshot):
                with self.subTest(version=version, file=path.name):
                    runtime.release.cache_clear()
                    parsed, entries, _ = self.assert_single_verified_read(path, runtime.release)
                    self.assertEqual(parsed['datasetVersion'], version)
                    self.assertEqual(len(entries), count)
                    self.assertEqual(runtime.snapshot_view(next(iter(entries)))['baseSnapshotId'], next(iter(entries)))

    def test_bad_snapshot_or_model_is_rejected_before_deserialization_and_can_retry(self):
        read_bytes = Path.read_bytes
        for runtime, manifest, _, version, count in RELEASES:
            metadata = json.loads(manifest.read_bytes())
            snapshot = runtime.ROOT / metadata['snapshots']
            model = runtime.ROOT / metadata['artifact']
            for target, missing in ((snapshot, False), (snapshot, True), (model, False)):
                with self.subTest(version=version, file=target.name, missing=missing):
                    runtime.release.cache_clear()

                    def substitute(path):
                        if path != target:
                            return read_bytes(path)
                        if missing:
                            raise FileNotFoundError(path)
                        return b'{corrupt'

                    with patch.object(Path, 'read_bytes', substitute), patch.object(runtime.joblib, 'load') as load:
                        if missing:
                            with self.assertRaises(FileNotFoundError):
                                runtime.release()
                        else:
                            self.assert_incompatible(runtime.release)
                        load.assert_not_called()
                    self.assertEqual(len(runtime.release()[1]), count)

    def test_pinned_but_invalid_manifest_json_or_version_is_rejected(self):
        read_bytes = Path.read_bytes
        for runtime, manifest, pin, version, _ in RELEASES:
            metadata = json.loads(manifest.read_bytes())
            incompatible = json.dumps(dict(metadata, datasetVersion='0.0.0')).encode()
            for payload, error in ((b'{corrupt', json.JSONDecodeError), (incompatible, historical.ScenarioError)):
                with self.subTest(version=version, error=error.__name__):
                    runtime.release.cache_clear()

                    def substitute(path):
                        return payload if path == manifest else read_bytes(path)

                    with patch.object(runtime, pin, hashlib.sha256(payload).hexdigest()), \
                            patch.object(Path, 'read_bytes', substitute), patch.object(runtime.joblib, 'load') as load:
                        with self.assertRaises(error) as caught:
                            runtime.release()
                        if error is historical.ScenarioError:
                            self.assertEqual(caught.exception.code, 'INCOMPATIBLE_ARTIFACT')
                        load.assert_not_called()

    def test_preview_uses_verified_saved_metrics_and_rejects_changed_report(self):
        read_bytes = Path.read_bytes
        for runtime, manifest, _, version, _ in RELEASES:
            with self.subTest(version=version):
                report = manifest.with_name('test-evaluation.json')
                metrics = json.loads(report.read_bytes())['model']
                payload = request(runtime.capabilities()['snapshots'][0])
                result = self.assert_single_verified_read(report, lambda: runtime.preview(payload))
                self.assertEqual(result['metrics'], dict(metrics, partition='FINAL_TEST_SAVED', origin='SYNTHETIC'))

                def substitute(path):
                    return b'{}' if path == report else read_bytes(path)

                with patch.object(Path, 'read_bytes', substitute):
                    self.assert_incompatible(lambda: runtime.preview(payload))
                self.assertEqual(runtime.preview(payload)['metrics'], result['metrics'])
