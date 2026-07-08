import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_MEMORY_PATH = Path(__file__).resolve().parents[2] / 'data' / 'review_memory.jsonl'
VALID_STATUSES = {'generated', 'accepted', 'resolved', 'falsePositive'}


def memory_path():
    return Path(os.environ.get('REVIEW_MEMORY_PATH', DEFAULT_MEMORY_PATH))


def persist_review_findings(project_id, mr_id, findings, path=None):
    if not findings:
        return 0

    target = Path(path) if path else memory_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = {record.get('findingId') for record in latest_memory_records(target)}

    count = 0
    with target.open('a', encoding='utf-8') as file:
        for finding in findings:
            record = build_memory_record(project_id, mr_id, finding)
            if record['findingId'] in existing_ids:
                continue
            file.write(json.dumps(record, ensure_ascii=False) + '\n')
            existing_ids.add(record['findingId'])
            count += 1
    return count


def find_historical_findings(project_id, file_path, categories, mr_id='', limit=3, path=None, query_text=''):
    target = Path(path) if path else memory_path()
    if not target.exists():
        return []

    wanted_categories = {category for category in categories if category}
    matches = []
    for record in latest_memory_records(target):
        if str(record.get('projectId')) != str(project_id):
            continue
        if mr_id and str(record.get('mrId')) == str(mr_id):
            continue
        if record.get('status') == 'falsePositive':
            continue

        score, reasons = score_memory_record(record, file_path, wanted_categories, query_text)
        if score > 0:
            matches.append({**record, 'reason': ', '.join(reasons), '_score': score})

    matches.sort(key=lambda item: item['_score'], reverse=True)
    return matches[:limit]


def build_memory_record(project_id, mr_id, finding):
    record = {
        'projectId': str(project_id),
        'mrId': str(mr_id or ''),
        'category': finding.get('category', ''),
        'severity': finding.get('severity', ''),
        'file': finding.get('file', ''),
        'line': str(finding.get('line', '')),
        'issue': finding.get('issue', ''),
        'suggestion': finding.get('suggestion', ''),
        'evidence': finding.get('evidence') or [],
        'status': normalize_status(finding.get('status', 'generated')),
        'createdAt': now_iso(),
    }
    record['findingId'] = finding.get('findingId') or stable_finding_id(record)
    return record


def stable_finding_id(record):
    payload = '|'.join([
        str(record.get('projectId', '')),
        str(record.get('mrId', '')),
        str(record.get('category', '')),
        str(record.get('severity', '')),
        str(record.get('file', '')),
        str(record.get('line', '')),
        str(record.get('issue', '')),
    ])
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()[:16]


def update_review_finding_status(project_id, mr_id, finding_id, status, path=None):
    status = normalize_status(status)
    target = Path(path) if path else memory_path()
    records = latest_memory_records(target)
    for record in records:
        if (str(record.get('projectId')) == str(project_id)
                and str(record.get('mrId')) == str(mr_id or '')
                and record.get('findingId') == finding_id):
            updated = {**record, 'status': status, 'updatedAt': now_iso()}
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('a', encoding='utf-8') as file:
                file.write(json.dumps(updated, ensure_ascii=False) + '\n')
            return True
    return False


def latest_memory_records(path):
    target = Path(path)
    if not target.exists():
        return []

    records_by_id = {}
    with target.open(encoding='utf-8') as file:
        for line in file:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            finding_id = record.get('findingId') or stable_finding_id(record)
            record['findingId'] = finding_id
            records_by_id[finding_id] = record
    return list(records_by_id.values())


def normalize_status(status):
    return status if status in VALID_STATUSES else 'generated'


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def score_memory_record(record, file_path, categories, query_text=''):
    score = 0
    reasons = []
    if record.get('file') == file_path:
        score += 3
        reasons.append('same file')
    if record.get('category') in categories:
        score += 2
        reasons.append(f"same category: {record.get('category')}")
    if query_text:
        overlap = token_overlap(query_text, f"{record.get('issue', '')} {record.get('suggestion', '')}")
        if overlap:
            score += min(overlap, 3)
            reasons.append(f"issue overlap: {overlap}")
    return score, reasons


def token_overlap(left, right):
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    return len(left_tokens & right_tokens)


def tokenize(text):
    return [token for token in ''.join(char.lower() if char.isalnum() else ' ' for char in text).split() if len(token) > 2]


def format_historical_findings(records):
    if not records:
        return ''

    formatted = []
    for index, record in enumerate(records, start=1):
        evidence = ', '.join(record.get('evidence') or [])
        location = f"{record.get('file', 'unknown')}:{record.get('line', 'changed block')}"
        formatted.append(
            f"[memory {index}: {record.get('severity', 'finding')} "
            f"{record.get('category', '')} {location}; reason={record.get('reason', '')}]\n"
            f"issue: {record.get('issue', '')}\n"
            f"suggestion: {record.get('suggestion', '')}\n"
            f"evidence: {evidence}"
        )
    return "\n\n---\n\n".join(formatted)
