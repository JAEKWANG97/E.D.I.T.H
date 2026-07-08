import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'review_output.py'
SPEC = importlib.util.spec_from_file_location('review_output_under_test', MODULE_PATH)
review_output = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_output)


class ReviewOutputTest(unittest.TestCase):

    def test_parses_fenced_json_and_renders_findings_html(self):
        payload = review_output.normalize_review_payload(review_output.parse_model_json("""```json
{
  "findings": [
    {
      "severity": "must_fix",
      "category": "auth",
      "file": "UserController.java",
      "line": 72,
      "issue": "refresh does not update cookie",
      "whyItMatters": "browser keeps using the expired HttpOnly cookie",
      "suggestion": "set the new accessToken cookie",
      "evidence": ["docs/review-rules/auth.md#Token Lifecycle"]
    }
  ],
  "summary": "Auth review",
  "techStacks": ["Java", "Spring"]
}
```"""))

        self.assertEqual(payload['techStacks'], ['Java', 'Spring'])
        self.assertEqual(payload['findings'][0]['file'], 'UserController.java')
        self.assertEqual(payload['findings'][0]['line'], 72)
        self.assertIn('<h4>Must Fix</h4>', payload['review'])
        self.assertIn('UserController.java:72', payload['review'])
        self.assertIn('docs/review-rules/auth.md#Token Lifecycle', payload['review'])

    def test_renders_empty_findings_as_non_blocking_review(self):
        payload = review_output.normalize_review_payload({
            'findings': [],
            'summary': 'No blocking findings.',
            'techStack': ['Python']
        })

        self.assertEqual(payload['techStacks'], ['Python'])
        self.assertIn('No blocking findings.', payload['review'])


if __name__ == '__main__':
    unittest.main()
