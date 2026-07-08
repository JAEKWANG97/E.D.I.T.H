import os
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path


PROJECT_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_PATH))

try:
    from app import create_app
except ModuleNotFoundError as exc:
    if exc.name != 'flask':
        raise
    create_app = None

MEMORY_MODULE_PATH = PROJECT_PATH / 'app' / 'services' / 'review_memory.py'
SPEC = importlib.util.spec_from_file_location('review_memory_under_test', MEMORY_MODULE_PATH)
review_memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_memory)


class ReviewMemoryRoutesTest(unittest.TestCase):

    def test_updates_review_memory_status(self):
        if create_app is None:
            self.skipTest('Flask is not installed in this Python environment')

        with tempfile.TemporaryDirectory() as temp_dir:
            memory_file = Path(temp_dir) / 'memory.jsonl'
            old_path = os.environ.get('REVIEW_MEMORY_PATH')
            os.environ['REVIEW_MEMORY_PATH'] = str(memory_file)
            try:
                review_memory.persist_review_findings('123', '7', [{
                    'severity': 'must_fix',
                    'category': 'auth',
                    'file': 'UserController.java',
                    'line': 72,
                    'issue': 'refresh does not update cookie',
                    'suggestion': 'set the new accessToken cookie',
                }])
                finding_id = review_memory.latest_memory_records(memory_file)[0]['findingId']
                app = create_app()

                response = app.test_client().post('/rag/review-memory/status', json={
                    'projectId': '123',
                    'mrId': '7',
                    'findingId': finding_id,
                    'status': 'falsePositive',
                })
            finally:
                if old_path is None:
                    os.environ.pop('REVIEW_MEMORY_PATH', None)
                else:
                    os.environ['REVIEW_MEMORY_PATH'] = old_path

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'success')


if __name__ == '__main__':
    unittest.main()
