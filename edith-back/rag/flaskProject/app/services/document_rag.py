import math
import re
from dataclasses import dataclass
from pathlib import Path


MAX_DOCUMENT_EVIDENCE_CHARS = 5000
VECTOR_SIZE = 128


@dataclass
class DocumentSection:
    content: str
    metadata: dict
    vector: list[float]


def split_front_matter(text):
    if not text.startswith('---\n'):
        return {}, text

    end = text.find('\n---\n', 4)
    if end == -1:
        return {}, text

    front_matter = text[4:end]
    body = text[end + 5:]
    return parse_front_matter(front_matter), body


def parse_front_matter(front_matter):
    metadata = {}
    current_key = None

    for raw_line in front_matter.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        if line.startswith('  - ') and current_key:
            metadata.setdefault(current_key, []).append(line[4:].strip())
            continue

        if ':' not in line:
            continue

        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        current_key = key

        if value:
            metadata[key] = value
        else:
            metadata[key] = []

    return metadata


def split_markdown_sections(body):
    sections = []
    current_heading = 'Overview'
    current_lines = []

    for line in body.splitlines():
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match and current_lines:
            sections.append((current_heading, '\n'.join(current_lines).strip()))
            current_heading = heading_match.group(2).strip()
            current_lines = [line]
        else:
            if heading_match:
                current_heading = heading_match.group(2).strip()
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, '\n'.join(current_lines).strip()))

    return [(heading, content) for heading, content in sections if content]


def tokenize(text):
    return re.findall(r'[a-zA-Z][a-zA-Z0-9_.-]*|[가-힣]+', text.lower())


def embed_text(text):
    vector = [0.0] * VECTOR_SIZE
    for token in tokenize(text):
        vector[hash(token) % VECTOR_SIZE] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left, right):
    return sum(a * b for a, b in zip(left, right))


def project_root_from_cloned_path(project_path):
    path = Path(project_path).resolve()
    for candidate in [path, *path.parents]:
        if (candidate / 'docs').exists():
            return candidate
    return path


def load_document_sections(project_path):
    docs_root = project_root_from_cloned_path(project_path) / 'docs'
    if not docs_root.exists():
        return []

    sections = []
    for doc_path in sorted(docs_root.rglob('*.md')):
        text = doc_path.read_text(encoding='utf-8')
        metadata, body = split_front_matter(text)
        relative_path = str(doc_path.relative_to(project_root_from_cloned_path(project_path)))

        for heading, content in split_markdown_sections(body):
            section_metadata = {
                **metadata,
                'source_path': relative_path,
                'heading': heading,
            }
            sections.append(DocumentSection(
                content=content,
                metadata=section_metadata,
                vector=embed_text(f"{section_metadata} {content}")
            ))

    return sections


def classify_change_categories(changes, mr_title='', mr_description='', target_branch=''):
    haystack = ' '.join([
        mr_title or '',
        mr_description or '',
        target_branch or '',
        *[change.get('path', '') for change in changes],
        *[change.get('diff', '') for change in changes],
    ]).lower()

    category_rules = {
        'auth': ['jwt', 'cookie', 'securityconfig', 'token', 'refresh', 'logout', 'signin', 'sign-in'],
        'api-contract': ['controller', 'response', 'request', 'dto', 'jsonproperty', 'resttemplate', 'techstacks'],
        'async': ['@async', 'executor', 'threadpool', 'webhook', 'queuecapacity'],
        'testing': ['test', 'assert', 'mock', 'contract', 'compatibility'],
        'rag-review': ['reviewer.py', 'rag', 'prompt', 'codereviewresponse', 'codereviewrequest'],
        'security': ['secret', 'password', 'encrypt', 'decrypt', 'credential', 'csrf', 'cors'],
        'operations': ['application.yml', 'dockerfile', 'jenkinsfile', 'env', 'webhook-url'],
        'persistence': ['repository', 'entity', 'redis', 'jpa', 'database', 'transaction'],
    }

    categories = []
    for category, keywords in category_rules.items():
        if any(keyword in haystack for keyword in keywords):
            categories.append(category)

    if not categories:
        categories.append('testing')

    risk_level = 'low'
    if any(category in categories for category in ['auth', 'security', 'api-contract', 'async']):
        risk_level = 'high'
    elif (target_branch or '').lower() in {'main', 'master', 'production', 'prod'}:
        risk_level = 'medium'
    elif len(categories) > 1:
        risk_level = 'medium'

    review_focus = {
        'auth': 'token lifecycle, cookie behavior, gateway/service consistency',
        'api-contract': 'serialized field names, caller compatibility, fallback shape',
        'async': 'failure containment, duplicate delivery, executor saturation',
        'testing': 'missing regression checks for the changed behavior',
        'rag-review': 'prompt grounding, parser fallback, Java client compatibility',
        'security': 'secret exposure, credential logging, trust-boundary validation',
        'operations': 'environment defaults, deployment-only failures, timeout behavior',
        'persistence': 'transaction boundaries, cache consistency, data integrity',
    }

    focus = [review_focus[category] for category in categories if category in review_focus]
    if (target_branch or '').lower() in {'main', 'master', 'production', 'prod'}:
        focus.append('production branch compatibility and rollback risk')

    return {
        'categories': categories,
        'riskLevel': risk_level,
        'reviewFocus': focus,
        'targetBranch': target_branch or '',
    }


def find_document_evidence(project_path, changes, mr_title='', mr_description='', target_branch='', limit=6):
    sections = load_document_sections(project_path)
    if not sections:
        return {
            'classification': classify_change_categories(changes, mr_title, mr_description, target_branch),
            'sections': [],
        }

    classification = classify_change_categories(changes, mr_title, mr_description, target_branch)
    query_text = ' '.join([
        mr_title or '',
        mr_description or '',
        target_branch or '',
        ' '.join(classification['categories']),
        ' '.join(change.get('path', '') for change in changes),
        ' '.join(change.get('diff', '')[:1500] for change in changes),
    ])
    query_vector = embed_text(query_text)

    scored = []
    for section in sections:
        score = cosine_similarity(query_vector, section.vector)
        metadata = section.metadata
        category = metadata.get('category')
        applies_to = metadata.get('applies_to', [])
        applies_to_values = applies_to if isinstance(applies_to, list) else [applies_to]
        source_path = metadata.get('source_path', '')

        if category in classification['categories']:
            score += 0.6
        score += document_type_priority(metadata.get('type'), classification['categories'])
        if any(value and value.lower() in query_text.lower() for value in applies_to_values):
            score += 0.35
        if any(category in source_path for category in classification['categories']):
            score += 0.2

        if score > 0:
            scored.append((score, section))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = select_document_sections(scored, limit)
    return {
        'classification': classification,
        'sections': [
            {
                'score': score,
                'content': section.content,
                'metadata': section.metadata,
                'reason': build_evidence_reason(section.metadata, classification),
            }
            for score, section in selected
        ],
    }


def select_document_sections(scored, limit):
    selected = []
    seen = set()

    for document_type in ['review-rule', 'api-contract', 'architecture-decision', 'architecture']:
        for score, section in scored:
            key = (section.metadata.get('source_path'), section.metadata.get('heading'))
            if key not in seen and section.metadata.get('type') == document_type:
                selected.append((score, section))
                seen.add(key)
                break

    for score, section in scored:
        if len(selected) >= limit:
            break
        key = (section.metadata.get('source_path'), section.metadata.get('heading'))
        if key not in seen:
            selected.append((score, section))
            seen.add(key)

    return selected[:limit]


def build_evidence_reason(metadata, classification):
    reasons = []
    category = metadata.get('category')
    if category in classification['categories']:
        reasons.append(f"same category: {category}")
    if metadata.get('type'):
        reasons.append(f"document type: {metadata['type']}")
    if metadata.get('applies_to'):
        applies_to = metadata['applies_to']
        if isinstance(applies_to, list):
            reasons.append("applies to: " + ', '.join(applies_to[:3]))
        else:
            reasons.append(f"applies to: {applies_to}")
    return '; '.join(reasons) if reasons else 'text similarity match'


def document_type_priority(document_type, categories):
    if document_type == 'review-rule':
        return 0.2
    if document_type == 'api-contract' and 'api-contract' in categories:
        return 0.25
    if document_type == 'architecture-decision':
        return 0.15
    if document_type == 'architecture':
        return 0.1
    return 0.0


def format_document_evidence(document_evidence, document_types=None):
    sections = document_evidence.get('sections', [])
    classification = document_evidence.get('classification', {})
    header = (
        f"categories={classification.get('categories', [])}, "
        f"riskLevel={classification.get('riskLevel', 'unknown')}, "
        f"targetBranch={classification.get('targetBranch', '')}, "
        f"reviewFocus={classification.get('reviewFocus', [])}"
    )
    if document_types:
        sections = [
            section for section in sections
            if section['metadata'].get('type') in document_types
        ]

    if not sections:
        return header + "\nNo project document evidence was retrieved."

    formatted = [header]
    for index, section in enumerate(sections, 1):
        metadata = section['metadata']
        source = metadata.get('source_path', 'unknown')
        heading = metadata.get('heading', 'Overview')
        formatted.append(
            f"[project rule {index}: {source}#{heading}]\n"
            f"reason: {section['reason']}\n"
            f"{section['content']}"
        )

    return truncate_text('\n\n---\n\n'.join(formatted), MAX_DOCUMENT_EVIDENCE_CHARS)


def format_classification(classification):
    return (
        f"categories={classification.get('categories', [])}\n"
        f"riskLevel={classification.get('riskLevel', 'unknown')}\n"
        f"targetBranch={classification.get('targetBranch', '')}\n"
        f"reviewFocus={classification.get('reviewFocus', [])}"
    )


def truncate_text(text, max_chars):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"
