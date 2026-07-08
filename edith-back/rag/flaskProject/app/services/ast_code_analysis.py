from importlib import import_module


LANGUAGE_MODULES = {
    'java': 'tree_sitter_java',
    'python': 'tree_sitter_python',
    'javascript': 'tree_sitter_javascript',
    'c': 'tree_sitter_c',
    'cpp': 'tree_sitter_cpp',
}

SYMBOL_NODE_TYPES = {
    'identifier',
    'type_identifier',
    'field_identifier',
    'property_identifier',
    'scoped_identifier',
}


def extract_ast_symbols(language, code):
    parser = build_parser(language)
    if parser is None or not code:
        return []

    code_bytes = code.encode('utf-8', errors='ignore')
    tree = parser.parse(code_bytes)
    symbols = []
    collect_symbols(tree.root_node, code_bytes, symbols)
    return sorted(set(symbols))[:30]


def build_parser(language):
    module_name = LANGUAGE_MODULES.get(language)
    if not module_name:
        return None

    try:
        from tree_sitter import Language, Parser
        language_module = import_module(module_name)
        return Parser(Language(language_module.language()))
    except Exception:
        return None


def collect_symbols(node, code_bytes, symbols):
    if node.type in SYMBOL_NODE_TYPES:
        text = code_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
        if len(text) > 1:
            symbols.append(text)

    for child in node.children:
        collect_symbols(child, code_bytes, symbols)
