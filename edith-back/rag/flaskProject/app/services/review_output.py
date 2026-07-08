import html
import json


SEVERITY_ORDER = ['must_fix', 'should_fix', 'nit', 'positive']


def parse_model_json(raw_result):
    cleaned = raw_result.strip()
    cleaned = cleaned.replace('```json', '').replace('```html', '').replace('```', '').strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and start < end:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def normalize_review_payload(raw_payload):
    payload = dict(raw_payload)
    findings = payload.get('findings') or []

    normalized_findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        normalized_findings.append({
            'severity': normalize_severity(finding.get('severity')),
            'category': finding.get('category', ''),
            'file': finding.get('file', ''),
            'line': finding.get('line', ''),
            'issue': finding.get('issue', ''),
            'whyItMatters': finding.get('whyItMatters') or finding.get('why_it_matters') or '',
            'suggestion': finding.get('suggestion', ''),
            'evidence': normalize_evidence(finding.get('evidence')),
        })

    payload['findings'] = normalized_findings
    payload['summary'] = payload.get('summary', '')
    payload['techStacks'] = payload.get('techStacks') or payload.get('techStack') or []
    payload['review'] = payload.get('review') or render_findings_html(normalized_findings, payload['summary'])
    return payload


def normalize_severity(value):
    value = (value or '').lower().replace('-', '_')
    return value if value in SEVERITY_ORDER else 'should_fix'


def normalize_evidence(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def render_findings_html(findings, summary=''):
    if not findings:
        escaped_summary = html.escape(summary) if summary else (
            'No blocking findings. The change looks reasonable based on the provided evidence.'
        )
        return f'<h3>Code Review</h3><p>{escaped_summary}</p>'

    sections = ['<h3>Code Review</h3>']
    for severity in SEVERITY_ORDER:
        severity_findings = [finding for finding in findings if finding['severity'] == severity]
        if not severity_findings:
            continue
        sections.append(f'<h4>{severity.replace("_", " ").title()}</h4>')
        sections.append('<ul>')
        for finding in severity_findings:
            location = format_location(finding)
            issue = html.escape(finding.get('issue', ''))
            why = html.escape(finding.get('whyItMatters', ''))
            suggestion = html.escape(finding.get('suggestion', ''))
            evidence = ', '.join(html.escape(item) for item in finding.get('evidence', []))
            evidence_text = f' <em>Evidence: {evidence}</em>' if evidence else ''
            sections.append(
                f'<li><strong>{html.escape(location)}</strong> - '
                f'{issue} / {why} / {suggestion}.{evidence_text}</li>'
            )
        sections.append('</ul>')
    return ''.join(sections)


def format_location(finding):
    file_path = finding.get('file') or 'unknown file'
    line = finding.get('line')
    return f'{file_path}:{line}' if line else file_path
