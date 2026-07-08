import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'review_memory.py'
SPEC = importlib.util.spec_from_file_location('review_memory_under_test', MODULE_PATH)
review_memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_memory)


class ReviewMemoryTest(unittest.TestCase):

    def test_persists_and_retrieves_matching_findings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'memory.jsonl'
            count = review_memory.persist_review_findings('123', '7', [
                {
                    'severity': 'must_fix',
                    'category': 'auth',
                    'file': 'UserController.java',
                    'line': 72,
                    'issue': 'refresh does not update cookie',
                    'suggestion': 'set the new accessToken cookie',
                    'evidence': ['docs/review-rules/auth.md#Token Lifecycle'],
                }
            ], path=path)

            matches = review_memory.find_historical_findings(
                '123',
                'UserController.java',
                ['auth'],
                mr_id='8',
                path=path
            )

        self.assertEqual(count, 1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['mrId'], '7')
        self.assertIn('findingId', matches[0])
        self.assertIn('same file', matches[0]['reason'])
        self.assertIn('same category: auth', matches[0]['reason'])

    def test_deduplicates_findings_by_stable_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'memory.jsonl'
            finding = {
                'severity': 'must_fix',
                'category': 'auth',
                'file': 'UserController.java',
                'line': 72,
                'issue': 'refresh does not update cookie',
                'suggestion': 'set the new accessToken cookie',
            }

            first_count = review_memory.persist_review_findings('123', '7', [finding], path=path)
            second_count = review_memory.persist_review_findings('123', '7', [finding], path=path)

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 0)

    def test_updates_status_and_skips_false_positives(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'memory.jsonl'
            review_memory.persist_review_findings('123', '7', [
                {
                    'severity': 'must_fix',
                    'category': 'auth',
                    'file': 'UserController.java',
                    'line': 72,
                    'issue': 'refresh does not update cookie',
                    'suggestion': 'set the new accessToken cookie',
                }
            ], path=path)
            finding_id = review_memory.latest_memory_records(path)[0]['findingId']

            updated = review_memory.update_review_finding_status(
                '123', '7', finding_id, 'falsePositive', path=path
            )
            matches = review_memory.find_historical_findings(
                '123', 'UserController.java', ['auth'], mr_id='8', path=path
            )

        self.assertTrue(updated)
        self.assertEqual(matches, [])

    def test_scores_issue_overlap(self):
        record = {
            'file': 'OtherController.java',
            'category': 'testing',
            'issue': 'refresh cookie is not updated',
            'suggestion': 'add refresh cookie regression test',
        }

        score, reasons = review_memory.score_memory_record(
            record,
            'UserController.java',
            {'auth'},
            'cookie refresh should update Set-Cookie'
        )

        self.assertGreater(score, 0)
        self.assertTrue(any(reason.startswith('issue overlap:') for reason in reasons))

    def test_formats_historical_findings_for_evidence_pack(self):
        formatted = review_memory.format_historical_findings([
            {
                'severity': 'must_fix',
                'category': 'auth',
                'file': 'UserController.java',
                'line': '72',
                'issue': 'refresh does not update cookie',
                'suggestion': 'set the new accessToken cookie',
                'evidence': ['docs/review-rules/auth.md#Token Lifecycle'],
                'reason': 'same category: auth',
            }
        ])

        self.assertIn('[memory 1: must_fix auth UserController.java:72', formatted)
        self.assertIn('same category: auth', formatted)
        self.assertIn('set the new accessToken cookie', formatted)


if __name__ == '__main__':
    unittest.main()
