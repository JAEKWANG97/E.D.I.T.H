import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'document_rag.py'
SPEC = importlib.util.spec_from_file_location('document_rag_under_test', MODULE_PATH)
document_rag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(document_rag)


class DocumentRagTest(unittest.TestCase):

    def test_loads_front_matter_and_heading_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / 'docs' / 'review-rules'
            docs.mkdir(parents=True)
            (docs / 'auth.md').write_text("""---
id: auth-review-rules
type: review-rule
category: auth
applies_to:
  - JwtUtil
  - CookieUtil
risk:
  - security
---

# Auth Rules

## Token Lifecycle

- Refresh endpoints must update the accessToken cookie.
""", encoding='utf-8')

            sections = document_rag.load_document_sections(tmp)

        self.assertEqual(len(sections), 2)
        token_section = sections[1]
        self.assertEqual(token_section.metadata['category'], 'auth')
        self.assertEqual(token_section.metadata['source_path'], 'docs/review-rules/auth.md')
        self.assertEqual(token_section.metadata['heading'], 'Token Lifecycle')
        self.assertIn('CookieUtil', token_section.metadata['applies_to'])

    def test_retrieves_category_matched_review_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / 'docs' / 'review-rules'
            docs.mkdir(parents=True)
            (docs / 'auth.md').write_text("""---
id: auth-review-rules
type: review-rule
category: auth
applies_to:
  - CookieUtil
---

# Auth Rules

## Cookie Safety

- HttpOnly cookie refresh must update Set-Cookie.
""", encoding='utf-8')
            (docs / 'async.md').write_text("""---
id: async-review-rules
type: review-rule
category: async
applies_to:
  - Webhook
---

# Async Rules

## Executor Safety

- Executor queues need visible failure modes.
""", encoding='utf-8')

            evidence = document_rag.find_document_evidence(tmp, [{
                'path': 'edith-back/user/src/main/java/UserController.java',
                'diff': '+ cookieUtil.addAccessToken(response, newAccessToken);'
            }], 'Fix refresh token cookie', '')

        self.assertIn('auth', evidence['classification']['categories'])
        self.assertEqual(evidence['sections'][0]['metadata']['category'], 'auth')
        self.assertIn('same category: auth', evidence['sections'][0]['reason'])

    def test_retrieves_api_and_adr_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            api_docs = Path(tmp) / 'docs' / 'api'
            adr_docs = Path(tmp) / 'docs' / 'adr'
            api_docs.mkdir(parents=True)
            adr_docs.mkdir(parents=True)
            (api_docs / 'rag-code-review.md').write_text("""---
id: api-rag-code-review
type: api-contract
category: rag-review
applies_to:
  - CodeReviewResponse
---

# API: RAG Code Review

## Response

- The response must preserve review, summary, techStacks, and additive findings.
""", encoding='utf-8')
            (adr_docs / 'rag-code-review-pipeline.md').write_text("""---
id: adr-rag-code-review-pipeline
type: architecture-decision
category: rag-review
applies_to:
  - reviewer.py
---

# ADR: RAG Code Review Pipeline

## Decision

- Structured findings JSON is the canonical review output.
""", encoding='utf-8')

            evidence = document_rag.find_document_evidence(tmp, [{
                'path': 'edith-back/rag/flaskProject/app/services/reviewer.py',
                'diff': '+ findings = jsonData.get("findings", [])'
            }], 'Keep CodeReviewResponse compatible', '', limit=4)

        sources = {section['metadata']['source_path'] for section in evidence['sections']}
        self.assertIn('docs/api/rag-code-review.md', sources)
        self.assertIn('docs/adr/rag-code-review-pipeline.md', sources)
        api_text = document_rag.format_document_evidence(evidence, {'api-contract'})
        adr_text = document_rag.format_document_evidence(evidence, {'architecture-decision'})
        self.assertIn('docs/api/rag-code-review.md', api_text)
        self.assertIn('docs/adr/rag-code-review-pipeline.md', adr_text)

    def test_keeps_representative_document_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            for folder, filename, doc_type in [
                ('review-rules', 'rag-review.md', 'review-rule'),
                ('api', 'rag-code-review.md', 'api-contract'),
                ('adr', 'rag-code-review-pipeline.md', 'architecture-decision'),
                ('architecture', 'rag-pipeline.md', 'architecture'),
            ]:
                docs = Path(tmp) / 'docs' / folder
                docs.mkdir(parents=True, exist_ok=True)
                (docs / filename).write_text(f"""---
id: {filename}
type: {doc_type}
category: rag-review
applies_to:
  - reviewer.py
---

# RAG Review

## Evidence

- reviewer.py findings should cite evidence.
""", encoding='utf-8')

            evidence = document_rag.find_document_evidence(tmp, [{
                'path': 'edith-back/rag/flaskProject/app/services/reviewer.py',
                'diff': '+ findings require evidence'
            }], 'RAG review evidence', '', limit=4)

        document_types = {section['metadata']['type'] for section in evidence['sections']}
        self.assertEqual(
            document_types,
            {'review-rule', 'api-contract', 'architecture-decision', 'architecture'}
        )

    def test_classifies_common_review_categories(self):
        cases = [
            ({
                'path': 'edith-back/developmentassistant/src/main/java/CodeReviewService.java',
                'diff': '+ @Async("codeReviewExecutor")\n+ executor.setQueueCapacity(50);'
            }, 'async'),
            ({
                'path': 'edith-back/rag/flaskProject/app/services/reviewer.py',
                'diff': '+ final_review_prompt = ChatPromptTemplate.from_template("...")'
            }, 'rag-review'),
            ({
                'path': 'edith-back/developmentassistant/src/main/resources/application.yml',
                'diff': '+ GITLAB_WEBHOOK_URL: ${GITLAB_WEBHOOK_URL}'
            }, 'operations'),
        ]

        for change, expected_category in cases:
            with self.subTest(expected_category=expected_category):
                classification = document_rag.classify_change_categories([change], '', '')
                self.assertIn(expected_category, classification['categories'])
                self.assertIn('riskLevel', classification)
                self.assertTrue(classification['reviewFocus'])

    def test_classifier_uses_target_branch(self):
        classification = document_rag.classify_change_categories([{
            'path': 'README.md',
            'diff': '+ docs only'
        }], '', '', 'main')

        self.assertEqual(classification['targetBranch'], 'main')
        self.assertEqual(classification['riskLevel'], 'medium')
        self.assertIn('production branch compatibility and rollback risk', classification['reviewFocus'])
        self.assertIn('targetBranch=main', document_rag.format_classification(classification))


if __name__ == '__main__':
    unittest.main()
