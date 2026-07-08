import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'code_metadata.py'
SPEC = importlib.util.spec_from_file_location('code_metadata_under_test', MODULE_PATH)
code_metadata = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(code_metadata)


class CodeMetadataTest(unittest.TestCase):

    def test_extracts_java_method_metadata(self):
        content = """
        @PostMapping("/token/refresh")
        public ApiResult<String> refreshToken(HttpServletResponse response) {
            String newAccessToken = userService.refreshAccessToken(refreshToken);
            cookieUtil.addAccessToken(response, newAccessToken);
            return success(newAccessToken);
        }
        """

        metadata = code_metadata.build_code_chunk_metadata(
            'edith-back/user/src/main/java/com/ssafy/edith/user/api/controller/UserController.java',
            'java',
            content
        )

        self.assertEqual(metadata['module'], 'user')
        self.assertEqual(metadata['className'], 'UserController')
        self.assertEqual(metadata['methodName'], 'refreshToken')
        self.assertEqual(metadata['content'], content)
        self.assertIn('@PostMapping("/token/refresh")', metadata['annotations'])
        self.assertIn('cookieUtil.addAccessToken', metadata['symbols'])
        self.assertIn('auth', metadata['categoryHints'])
        self.assertIn('api-contract', metadata['categoryHints'])

    def test_extracts_python_function_metadata(self):
        content = """
        def getCodeReview(url, token, projectId, branch, changes):
            return reviewer.getCodeReview(url, token, projectId, branch, changes)
        """

        metadata = code_metadata.build_code_chunk_metadata(
            'edith-back/rag/flaskProject/app/services/reviewer.py',
            'python',
            content
        )

        self.assertEqual(metadata['kind'], 'function')
        self.assertEqual(metadata['methodName'], 'getCodeReview')
        self.assertIn('rag-review', metadata['categoryHints'])

    def test_extracts_javascript_function_metadata(self):
        content = """
        const refreshToken = async () => {
            return apiClient.post('/api/v1/users/token/refresh');
        }
        """

        metadata = code_metadata.build_code_chunk_metadata(
            'frontend/src/api/auth.js',
            'javascript',
            content
        )

        self.assertEqual(metadata['kind'], 'function')
        self.assertEqual(metadata['className'], 'auth')
        self.assertEqual(metadata['methodName'], 'refreshToken')
        self.assertIn('auth', metadata['categoryHints'])


if __name__ == '__main__':
    unittest.main()
