import re
from pathlib import Path


def build_code_chunk_metadata(path, language, content):
    return {
        'path': path,
        'module': infer_module(path),
        'language': language,
        'kind': infer_kind(language),
        'className': infer_class_name(path, content),
        'methodName': infer_method_name(language, content),
        'annotations': ', '.join(extract_annotations(content)),
        'symbols': ', '.join(extract_symbols(content)),
        'categoryHints': ', '.join(infer_category_hints(path, content)),
        'content': content,
    }


def infer_module(path):
    parts = Path(path).parts
    if 'edith-back' in parts:
        index = parts.index('edith-back')
        if index + 1 < len(parts):
            return parts[index + 1]
    return parts[0] if parts else 'unknown'


def infer_kind(language):
    if language == 'java':
        return 'method'
    if language == 'python':
        return 'function'
    if language == 'javascript':
        return 'function'
    return 'code'


def infer_class_name(path, content):
    match = re.search(r'\b(?:class|interface|record|enum)\s+([A-Z][A-Za-z0-9_]*)', content)
    if match:
        return match.group(1)
    stem = Path(path).stem
    return stem if stem else 'unknown'


def infer_method_name(language, content):
    patterns = []
    if language == 'java':
        patterns = [
            r'\b(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\], ?]+\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(',
        ]
    elif language == 'python':
        patterns = [r'\bdef\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(']
    elif language == 'javascript':
        patterns = [
            r'\bfunction\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(',
            r'\b([a-zA-Z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            r'\b([a-zA-Z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{',
        ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return 'unknown'


def extract_annotations(content):
    return sorted(set(re.findall(r'@\w+(?:\([^)]*\))?', content)))[:8]


def extract_symbols(content):
    dotted_calls = re.findall(r'\b[a-zA-Z_][A-Za-z0-9_]*\.[a-zA-Z_][A-Za-z0-9_]*\b', content)
    class_like = re.findall(r'\b[A-Z][A-Za-z0-9_]{2,}\b', content)
    symbols = [*dotted_calls, *class_like]
    return sorted(set(symbols))[:20]


def infer_category_hints(path, content):
    haystack = f"{path}\n{content}".lower()
    rules = {
        'auth': ['jwt', 'cookie', 'token', 'securityconfig', 'signin', 'sign-in', 'logout'],
        'api-contract': ['controller', 'request', 'response', 'dto', 'jsonproperty', 'resttemplate'],
        'async': ['@async', 'executor', 'threadpool', 'webhook'],
        'rag-review': ['rag', 'reviewer', 'codereviewrequest', 'codereviewresponse', 'prompt'],
        'security': ['secret', 'password', 'encrypt', 'decrypt', 'credential'],
        'operations': ['application.yml', 'dockerfile', 'jenkinsfile', 'env'],
        'persistence': ['repository', 'entity', 'redis', 'jpa', 'transaction'],
        'testing': ['test', 'assert', 'mock'],
    }
    return [category for category, keywords in rules.items() if any(keyword in haystack for keyword in keywords)]
