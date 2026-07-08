import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'app' / 'services' / 'ast_code_analysis.py'
SPEC = importlib.util.spec_from_file_location('ast_code_analysis_under_test', MODULE_PATH)
ast_code_analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ast_code_analysis)


class FakeNode:
    def __init__(self, node_type, start=0, end=0, children=None):
        self.type = node_type
        self.start_byte = start
        self.end_byte = end
        self.children = children or []


class AstCodeAnalysisTest(unittest.TestCase):

    def test_collects_tree_sitter_identifier_symbols(self):
        code = b'cookieUtil.addAccessToken(response)'
        root = FakeNode('call_expression', children=[
            FakeNode('identifier', 0, 10),
            FakeNode('field_identifier', 11, 25),
            FakeNode('identifier', 26, 34),
        ])
        symbols = []

        ast_code_analysis.collect_symbols(root, code, symbols)

        self.assertEqual(symbols, ['cookieUtil', 'addAccessToken', 'response'])


if __name__ == '__main__':
    unittest.main()
