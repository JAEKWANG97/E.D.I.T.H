import importlib.util
import sys
import types
import unittest
from pathlib import Path


class Dummy:
    def __init__(self, *args, **kwargs):
        pass


def load_reviewer():
    modules = {
        'app': types.ModuleType('app'),
        'app.chunking': types.ModuleType('app.chunking'),
        'app.chunking.get_code': types.ModuleType('app.chunking.get_code'),
        'app.services': types.ModuleType('app.services'),
        'app.services.code_metadata': types.ModuleType('app.services.code_metadata'),
        'app.services.document_rag': types.ModuleType('app.services.document_rag'),
        'app.services.embeddings': types.ModuleType('app.services.embeddings'),
        'app.services.llm_model': types.ModuleType('app.services.llm_model'),
        'app.services.review_memory': types.ModuleType('app.services.review_memory'),
        'app.services.review_output': types.ModuleType('app.services.review_output'),
        'langchain_core': types.ModuleType('langchain_core'),
        'langchain_core.output_parsers': types.ModuleType('langchain_core.output_parsers'),
        'langchain': types.ModuleType('langchain'),
        'langchain.memory': types.ModuleType('langchain.memory'),
        'langchain_core.prompts': types.ModuleType('langchain_core.prompts'),
        'langchain.text_splitter': types.ModuleType('langchain.text_splitter'),
    }
    modules['app.chunking.get_code'].GitLabCodeChunker = Dummy
    modules['app.services.code_metadata'].build_code_chunk_metadata = lambda path, language, content: {}
    modules['app.services.code_metadata'].extract_symbols = lambda content: []
    modules['app.services.document_rag'].find_document_evidence = lambda *args, **kwargs: {}
    modules['app.services.document_rag'].format_classification = lambda classification: ''
    modules['app.services.document_rag'].format_document_evidence = lambda evidence: ''
    modules['app.services.embeddings'].CodeEmbeddingProcessor = Dummy
    modules['app.services.llm_model'].LLMModel = Dummy
    modules['app.services.review_memory'].find_historical_findings = lambda *args, **kwargs: []
    modules['app.services.review_memory'].format_historical_findings = lambda records: ''
    modules['app.services.review_memory'].persist_review_findings = lambda *args, **kwargs: 0
    modules['app.services.review_output'].normalize_review_payload = lambda payload: payload
    modules['app.services.review_output'].parse_model_json = lambda raw: {}
    modules['langchain_core.output_parsers'].StrOutputParser = Dummy
    modules['langchain.memory'].ConversationBufferMemory = Dummy
    modules['langchain_core.prompts'].ChatPromptTemplate = Dummy
    modules['langchain.text_splitter'].TokenTextSplitter = Dummy
    sys.modules.update(modules)

    module_path = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'reviewer.py'
    spec = importlib.util.spec_from_file_location('reviewer_under_test', module_path)
    reviewer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reviewer)
    return reviewer


class ReviewerRerankingTest(unittest.TestCase):

    def test_rerank_prefers_related_metadata_over_raw_distance(self):
        reviewer = load_reviewer()
        results = [
            {
                'score': 0.1,
                'path': 'other/GenericController.java',
                'content': 'public void generic() {}',
                'metadata': {
                    'path': 'other/GenericController.java',
                    'categoryHints': 'api-contract',
                    'symbols': '',
                },
            },
            {
                'score': 0.4,
                'path': 'edith-back/user/src/main/java/UserController.java',
                'content': 'cookieUtil.addAccessToken(response, token);',
                'metadata': {
                    'path': 'edith-back/user/src/main/java/UserController.java',
                    'categoryHints': 'auth, api-contract',
                    'symbols': 'cookieUtil.addAccessToken',
                    'className': 'UserController',
                },
            },
        ]

        reranked = reviewer.rerank_code_results(
            results,
            'edith-back/user/src/main/java/UserController.java',
            ['auth'],
            ['cookieUtil.addAccessToken']
        )

        self.assertEqual(reranked[0]['path'], 'edith-back/user/src/main/java/UserController.java')
        self.assertIn('same category: auth', reranked[0]['reason'])
        self.assertIn('symbol overlap: cookieUtil.addAccessToken', reranked[0]['reason'])

    def test_builds_evidence_pack_sections(self):
        reviewer = load_reviewer()

        evidence_pack = reviewer.build_evidence_pack({
            'path': 'UserController.java',
            'language': 'java',
            'classification': 'categories=[auth]\nriskLevel=high',
            'changed_blocks': '@@ line 72 @@',
            'surrounding_context': 'refreshToken(...)',
            'similar_codes': 'CookieUtil.addAccessToken(...)',
            'project_rules': 'docs/review-rules/auth.md#Token Lifecycle',
            'api_contracts': 'docs/api/user-auth.md#Endpoints',
            'architecture_decisions': 'docs/adr/auth-token-policy.md#Decision',
            'historical_findings': 'previous auth finding',
        })

        self.assertIn('## Change', evidence_pack)
        self.assertIn('## Classification', evidence_pack)
        self.assertIn('## Related Code / Similar Implementations', evidence_pack)
        self.assertIn('## Project Rule Evidence', evidence_pack)
        self.assertIn('## API Contract Evidence', evidence_pack)
        self.assertIn('## Architecture Decision Evidence', evidence_pack)
        self.assertIn('## Historical Review Findings', evidence_pack)
        self.assertIn('docs/review-rules/auth.md#Token Lifecycle', evidence_pack)
        self.assertIn('docs/api/user-auth.md#Endpoints', evidence_pack)


if __name__ == '__main__':
    unittest.main()
