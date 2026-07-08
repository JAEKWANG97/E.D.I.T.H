# reviewer.py
import os
from pathlib import Path
import re
from app.chunking.get_code import GitLabCodeChunker
from app.services.embeddings import CodeEmbeddingProcessor
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain.text_splitter import TokenTextSplitter
from app.services.llm_model import LLMModel
import uuid
import json
import logging

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 6000
MAX_SIMILAR_CODE_CHARS = 1400
MAX_RETRIEVAL_QUERY_CHARS = 2500


def getCodeReview(url, token, projectId, branch, changes, mr_title='', mr_description=''):
    chunker = None
    vectorDB = None
    uuid = generate_uuid()

    try:
        # 0. DB 초기화
        vectorDB = CodeEmbeddingProcessor(uuid)
        # 1. git Clone
        chunker = GitLabCodeChunker(
            gitlab_url=url,
            gitlab_token=token,
            project_id=projectId,
            local_path='./cloneRepo/' + projectId,
            branch=branch
        )

        # 2. 파일별 임베딩
        project_path = chunker.clone_project()
        if not project_path:
            return '', '', []

        # 3. 리뷰 할 코드들 메서드 Chunking
        file_chunks = []

        # changes 에 포함된 파일 확장자 정보 미리 저장
        relevant_extensions = set()
        for change in changes:
            relevant_extensions.add(get_language_from_extension(change['path']))

        for root, _, files in os.walk(project_path):
            for file in files:
                file_path = Path(root) / file

                # 불필요한 파일/폴더 제외
                if ('.git' in str(file_path)
                        or any(part.startswith('.') for part in file_path.parts)
                        or any(part.startswith('node_modules') for part in file_path.parts)):
                    continue

                # 파일 언어 확인
                language = chunker.get_file_language(str(file_path))
                if not language:
                    continue

                # changes 의 path 필드에 존재하는 파일 확장자명만 임베딩
                if language in relevant_extensions:
                    chunks = chunker.chunk_file(str(file_path), language)
                    relative_path = str(file_path.relative_to(project_path))
                    for chunk in chunks:
                        file_chunks.append({
                            'text': chunk,
                            'path': relative_path,
                            'language': language
                        })

        vectorDB.store_embeddings(file_chunks)

        review_queries = []  # path, diff (전문), 참고할 코드 (메서드)
        for change in changes:
            language = get_language_from_extension(change['path'])

            if (language == ''):
                continue

            diff = change.get('diff', '')
            changed_blocks = parse_changed_blocks(diff)
            changed_file_context = build_changed_file_context(project_path, change['path'], changed_blocks, chunker,
                                                              language)
            retrieval_queries = build_retrieval_queries(diff, changed_blocks, changed_file_context)
            similar_codes = query_relevant_code(vectorDB, retrieval_queries)

            review_queries.append({
                'path': change['path'],
                'language': language,
                'diff': diff,
                'changed_blocks': format_changed_blocks(changed_blocks),
                'surrounding_context': changed_file_context,
                'similar_codes': format_similar_codes(similar_codes)
            })

        # 5. 메서드 별 관련 코드 가져와 리트리버 생성, 질의
        llm_model = LLMModel()
        llm = llm_model.llm

        # 6. LLM 에 질의해 결과 반환
        result = get_code_review(projectId, branch, review_queries, llm, mr_title, mr_description)
        return result


    except Exception as e:
        logger.info(f"오류 발생: {e}")
        return '', '', []

    finally:
        # 리소스 정리
        if vectorDB:
            try:
                vectorDB.cleanup()
            except Exception as e:
                logger.info(f"Error cleaning up vectorDB: {e}")
        if chunker:
            try:
                chunker.cleanup_project_directory()
            except Exception as e:
                logger.info(f"Error cleaning up project directory: {e}")


def get_language_from_extension(file_name: str) -> str:
    extension = file_name.split('.')[-1].lower()  # 확장자 추출
    # 확장자별 언어 매핑
    language_map = {
        'py': 'python',
        'java': 'java',
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'javascript',
        'tsx': 'javascript',
        'c': 'c',
        'cpp': 'cpp',
        'h': 'c',
        'hpp': 'cpp'
    }
    return language_map.get(extension, '')


def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def truncate_text(text, max_chars):
    if not text:
        return ''
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def default_if_blank(value, fallback):
    if value is None or str(value).strip() == '':
        return fallback
    return value


def normalize_code_line(line):
    return re.sub(r'\s+', ' ', line).strip()


def parse_changed_blocks(diff_string):
    blocks = []
    current_block = None
    new_line_number = None

    def flush_block():
        nonlocal current_block
        if current_block and current_block['lines']:
            blocks.append(current_block)
        current_block = None

    for raw_line in diff_string.split('\n'):
        hunk_match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', raw_line)
        if hunk_match:
            flush_block()
            new_line_number = int(hunk_match.group(1))
            continue

        if raw_line.startswith('+++') or raw_line.startswith('---'):
            continue

        if raw_line.startswith('+'):
            if current_block is None:
                current_block = {
                    'start_line': new_line_number,
                    'end_line': new_line_number,
                    'lines': []
                }
            current_block['lines'].append(raw_line[1:])
            current_block['end_line'] = new_line_number
            if new_line_number is not None:
                new_line_number += 1
        elif raw_line.startswith('-'):
            flush_block()
        else:
            flush_block()
            if new_line_number is not None:
                new_line_number += 1

    flush_block()
    return blocks


def format_changed_blocks(changed_blocks):
    if not changed_blocks:
        return 'No added or modified lines were detected in the diff.'

    formatted_blocks = []
    for block in changed_blocks:
        start_line = block.get('start_line')
        end_line = block.get('end_line')
        if start_line is None:
            line_ref = "changed block"
        elif start_line == end_line:
            line_ref = f"line {start_line}"
        else:
            line_ref = f"lines {start_line}-{end_line}"
        formatted_blocks.append(f"@@ {line_ref} @@\n" + "\n".join(block.get('lines', [])))
    return "\n\n".join(formatted_blocks)


def find_relevant_chunks(file_content, file_chunks, changed_blocks):
    changed_lines = [
        normalize_code_line(line)
        for block in changed_blocks
        for line in block.get('lines', [])
        if normalize_code_line(line)
    ]
    relevant_chunks = []

    for chunk in file_chunks:
        normalized_chunk = normalize_code_line(chunk)
        if any(line and line in normalized_chunk for line in changed_lines):
            relevant_chunks.append(chunk)

    if relevant_chunks:
        return relevant_chunks

    file_lines = file_content.splitlines()
    windows = []
    for block in changed_blocks:
        start_line = block.get('start_line')
        end_line = block.get('end_line')
        if not start_line or not end_line:
            continue
        start = max(0, start_line - 8)
        end = min(len(file_lines), end_line + 7)
        numbered_lines = [
            f"{idx + 1}: {file_lines[idx]}"
            for idx in range(start, end)
        ]
        windows.append("\n".join(numbered_lines))
    return windows


def build_changed_file_context(project_path, changed_path, changed_blocks, chunker, language):
    file_path = Path(project_path) / changed_path
    if not file_path.exists():
        return 'Changed file is not present in the checked-out target branch.'

    try:
        file_content = read_text_file(file_path)
        file_chunks = chunker.chunk_file(str(file_path), language)
        relevant_chunks = find_relevant_chunks(file_content, file_chunks, changed_blocks)
        if not relevant_chunks:
            return truncate_text(file_content, MAX_CONTEXT_CHARS)

        labeled_chunks = []
        for index, chunk in enumerate(relevant_chunks[:4], 1):
            labeled_chunks.append(f"[context {index}: {changed_path}]\n{chunk}")
        return truncate_text("\n\n".join(labeled_chunks), MAX_CONTEXT_CHARS)
    except Exception as e:
        logger.info(f"Failed to build changed file context for {changed_path}: {e}")
        return 'Changed file context could not be loaded.'


def build_retrieval_queries(diff, changed_blocks, changed_file_context):
    queries = []
    for block in changed_blocks:
        block_text = "\n".join(block.get('lines', []))
        if len(normalize_code_line(block_text)) >= 30:
            queries.append(truncate_text(block_text, MAX_RETRIEVAL_QUERY_CHARS))

    if changed_file_context and changed_file_context not in {
        'Changed file is not present in the checked-out target branch.',
        'Changed file context could not be loaded.'
    }:
        queries.append(truncate_text(changed_file_context, MAX_RETRIEVAL_QUERY_CHARS))

    if not queries:
        queries.append(truncate_text(diff, MAX_RETRIEVAL_QUERY_CHARS))

    return queries[:3]


def query_relevant_code(vectorDB, retrieval_queries):
    results = []
    seen = set()
    for query in retrieval_queries:
        for item in vectorDB.query_similar_code(query, 4):
            content = item.get('content') if isinstance(item, dict) else str(item)
            fingerprint = normalize_code_line(content)[:300]
            if not fingerprint or fingerprint in seen:
                continue
            seen.add(fingerprint)
            results.append(item)
    return results[:6]


def format_similar_codes(similar_codes):
    if not similar_codes:
        return 'No relevant existing code was retrieved.'

    formatted = []
    for index, item in enumerate(similar_codes, 1):
        if isinstance(item, dict):
            path = item.get('path', 'unknown')
            language = item.get('language', 'unknown')
            content = item.get('content', '')
            formatted.append(
                f"[similar {index}: {path} ({language})]\n"
                f"{truncate_text(content, MAX_SIMILAR_CODE_CHARS)}"
            )
        else:
            formatted.append(f"[similar {index}: unknown]\n{truncate_text(str(item), MAX_SIMILAR_CODE_CHARS)}")
    return "\n\n---\n\n".join(formatted)


def parse_review_json(raw_result):
    cleaned = raw_result.strip()
    cleaned = cleaned.replace('```json', '').replace('```html', '').replace('```', '').strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and start < end:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def get_code_review(projectId, branch, review_queries, llm, mr_title='', mr_description=''):
    uuid = generate_uuid()
    portfolio_memory = ConversationBufferMemory(
        memory_key=f"{projectId}_portfolio_{uuid}",
        max_token_limit=4000,
        return_messages=True,
        prompt="""해당 코드리뷰를 참고해 포트폴리오를 만들 해당 MR 의 기술스택, 트러블 슈팅 등을 기록할 수 있게 요약해"""
    )

    code_review_memory = ConversationBufferMemory(
        memory_key=f"{projectId}_code_review_{uuid}",
        max_token_limit=4000,
        return_messages=True,
        prompt="""해당 요약본 으로 전체 코드리뷰를 작성하기 위해 중요한 기능, 수정 해야 할 사항, 에러 발생 원인, 트러블 슈팅을 요약해줘"""
    )

    review_prompt = ChatPromptTemplate.from_template("""
    당신은 시니어 백엔드/풀스택 엔지니어로서 MR 코드리뷰를 수행합니다.
    목표는 변경 설명이 아니라 실제 결함, 회귀 위험, 계약 변경, 보안, 예외 처리, 테스트 누락을 찾는 것입니다.
    근거가 약하면 지적하지 마세요. 문제가 없으면 "no finding"이라고 명시하세요.

    MR 제목: {mr_title}
    MR 설명: {mr_description}
    대상 브랜치: {branch}

    파일: {file_path}

    === 변경된 코드 (git diff) ===
    {code_chunk}

    === 변경 블록과 라인 참조 ===
    {changed_blocks}

    === 변경 파일 주변 컨텍스트 ===
    {surrounding_context}

    === 참고할 기존 유사 코드 ===
    {similar_codes}

    다음 형식으로만 작성하세요.
    - must_fix: 실제 버그, 보안 문제, 계약 위반, 운영 장애 가능성이 있는 항목
    - should_fix: 유지보수성, 예외 처리, 테스트 누락 등 merge 전에 고치면 좋은 항목
    - nit: 작은 스타일/가독성 항목. 없으면 생략
    - positive: 유지할 만한 좋은 변경. 없으면 생략

    각 finding은 반드시 아래 정보를 포함하세요.
    - file: 파일 경로
    - line: diff의 라인 또는 changed block 참조. 모르면 "changed block"이라고 쓰세요.
    - issue: 무엇이 문제인지 한 문장
    - why_it_matters: 실제 영향
    - suggestion: 구체적인 수정 방향

    금지:
    - 변경사항을 길게 요약하지 마세요.
    - 모든 카테고리를 억지로 채우지 마세요.
    - 참고 코드가 직접 관련 없으면 언급하지 마세요.
    - 추측성 보안/성능 지적을 만들지 마세요.
    """)

    final_review_prompt = ChatPromptTemplate.from_template("""
        해당 MR의 전체 코드리뷰를 GitLab MR Comment 형식으로 작성해주세요.
        설명식 요약보다 수정 가능한 finding을 우선하세요.
        실제 문제가 없는 카테고리는 비워두거나 생략하세요.

        * 중요: 응답은 JSON 형식으로 다음 구조를 따라 작성해주세요:
        * techStack 은 ["JavaScript", "TypeScript", "HTML5", "CSS3", "Sass", "Bootstrap", "TailwindCSS", "React", "Angular", 
  "Vue", "Svelte", "jQuery", "Node", "Express", "NestJS", "NextJS", "NuxtJS", "Python", "Django", "Flask", 
  "Java", "Spring", "PHP", "Laravel", "Ruby", "Rails", "CSharp", "DotNet", "Cplusplus", "Go", "Rust", 
  "Swift", "Kotlin", "Docker", "Kubernetes", "AWS", "Firebase", "GoogleCloud", "Azure", "Heroku", 
  "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "GraphQL", "Apollo", "Git", "GitHub", 
  "GitLab", "Bitbucket", "Jenkins", "TravisCI", "CircleCI", "NGINX", "Vercel"] 해당 배열 안에서 골라줘
  
        {{
            "review": "<코드리뷰 내용을 HTML 형식으로 작성>",
            "techStack": ["사용된 기술스택 목록"]
        }}

        MR 제목: {mr_title}
        MR 설명: {mr_description}
        대상 브랜치: {branch}

        ===파일별 리뷰 근거===
        {history}

        review HTML은 다음 구조를 따르세요.
        <h3>Code Review</h3>
        <h4>Must Fix</h4>
        <ul><li><strong>파일:라인</strong> - 문제 / 영향 / 제안</li></ul>
        <h4>Should Fix</h4>
        <ul><li><strong>파일:라인</strong> - 문제 / 영향 / 제안</li></ul>
        <h4>Nit</h4>
        <ul><li><strong>파일:라인</strong> - 문제 / 제안</li></ul>
        <h4>Positive</h4>
        <ul><li><strong>파일</strong> - 유지할 만한 좋은 변경</li></ul>

        finding이 하나도 없으면 review에 다음 문장만 포함하세요:
        <h3>Code Review</h3><p>No blocking findings. The change looks reasonable based on the provided diff and context.</p>

        응답은 반드시 위의 JSON 형식을 준수해야 하며, HTML 내용은 실제 복사-붙여넣기가 가능해야 합니다.
        techStack 배열에는 코드에서 사용된 주요 기술들(SpringBoot, React 등)을 포함해주세요.
    """)

    portfolio_prompt = ChatPromptTemplate.from_template("""
    당신은 포트폴리오 작성을 돕는 전문가입니다. MR(Merge Request)의 내용을 분석하여 포트폴리오에 필요한 핵심 정보만을 간단명료하게 추출해주세요.

    주어진 MR 내용: {history}

    다음 형식으로 핵심 정보만 추출하여 응답해주세요:

    [기술 스택]
    - 사용된 핵심 기술만 나열 (프레임워크, 라이브러리, 도구 등)
    - 각 기술의 버전은 중요한 경우에만 표기

    [구현 기능]
    - bullet point로 3줄 이내 정리
    - 각 기능은 "~구현", "~개발" 형식으로 끝내기
    - 기술적으로 의미있는 내용만 포함

    [문제 해결]
    - 가장 중요한 기술적 도전/해결 1-2개만 선택
    - "문제: ~" / "해결: ~" 형식으로 작성
    - 실제 구현/해결한 내용만 포함 (개선해야할 사항 제외, 트러블 슈팅 내역으로)

    응답 시 주의사항:
    1. 모든 내용은 간단명료하게 작성
    2. 일반적이거나 당연한 내용은 제외
    3. 기술적으로 차별화된 내용만 포함
    4. 구체적인 기술/도구명 사용
    """)

    # 체인 구성
    review_chain = review_prompt | llm | StrOutputParser()
    portfolio_chain = portfolio_prompt | llm | StrOutputParser()
    final_review_chain = final_review_prompt | llm | StrOutputParser()

    try:
        for review_query in review_queries:

            try:
                review_result = chunked_review(projectId, llm, review_query, review_chain, code_review_memory,
                                               branch, mr_title, mr_description)

                portfolio_memory.save_context(
                    {"input": f"Review for {review_query['path']}"},
                    {"output": review_result}
                )
            except Exception as e:
                logger.info(f"개별 리뷰 중 오류 발생: {e}")
                continue

        portfolio_result = portfolio_chain.invoke({
            "input": "Generate final portfolio",
            "history": portfolio_memory.load_memory_variables({})[f"{projectId}_portfolio_{uuid}"]
        })

        code_review_result = final_review_chain.invoke({
            "input": "Generate final review",
            "history": code_review_memory.load_memory_variables({})[f"{projectId}_code_review_{uuid}"],
            "branch": branch,
            "mr_title": default_if_blank(mr_title, "Unavailable"),
            "mr_description": default_if_blank(mr_description, "Unavailable")
        })

        try:
            # 2. 문자열을 JSON으로 파싱
            jsonData = parse_review_json(code_review_result)
            logger.info(jsonData)
            # 3. 파싱된 JSON 데이터 사용
            logger.info(f"{jsonData['review']}\n === \n{jsonData.get('techStack', [])}")

            return re.sub(r'<title>.*?</title>', '', jsonData['review'].replace('\n', '')), portfolio_result, jsonData.get(
                'techStack', [])
        except json.JSONDecodeError as e:
            logger.info(f"JSON 파싱 에러: {e}")
            fallback_review = (
                "<h3>Code Review</h3>"
                "<p>Review generation completed, but the model response was not valid JSON. "
                "Please retry the review.</p>"
            )
            return fallback_review, portfolio_result, []

    except Exception as e:
        logger.info(f"리뷰 중 오류 발생: {e}")
        return str(e), '', []

    finally:
        portfolio_memory.clear()
        code_review_memory.clear()


def parse_git_diff(diff_string):
    # diff 헤더(@@ -0,0 +1,30 @@) 이후부터 파싱
    lines = diff_string.split('\n')
    start_idx = 0

    # diff 헤더 찾기
    for i, line in enumerate(lines):
        if line.startswith('@@'):
            start_idx = i + 1
            break

    removed_lines = []
    added_lines = []

    # 실제 코드 변경사항 파싱
    for line in lines[start_idx:]:
        # 빈 줄 무시
        if not line:
            continue

        # 삭제된 라인('-'로 시작)
        if line.startswith('-'):
            removed_lines.append(line[1:])  # '-' 제외하고 저장
        # 추가된 라인('+'로 시작)
        elif line.startswith('+'):
            added_lines.append(line[1:])  # '+' 제외하고 저장

    return removed_lines, added_lines


def chunked_review(project_id, llm, review_query: dict, review_chain, code_review_memory,
                   branch, mr_title='', mr_description='',
                   max_token_limit: int = 4000) -> str:
    uuid = generate_uuid()
    file_path = review_query['path']
    file_codeReview_memory = ConversationBufferMemory(
        memory_key=f"{project_id}_codereview_history_{uuid}",
        max_token_limit=4000,
        return_messages=True,
        prompt="""해당 파일의 코드리뷰 finding만 보존해. 설명 요약보다 must_fix, should_fix, nit, positive 항목과 근거를 우선해."""
    )

    try:
        # 토큰 스플리터 설정
        splitter = TokenTextSplitter(
            chunk_size=max_token_limit // 2,
            chunk_overlap=100  # 문맥 유지를 위한 중복
        )

        # 코드 청크 분할
        code_chunks = splitter.split_text(review_query['diff']) or [review_query['diff']]

        # 각 코드 청크에 대해 리뷰 수행
        for i, chunk in enumerate(code_chunks):
            try:
                result = review_chain.invoke({
                    "file_path": f"{file_path} (Part {i + 1}/{len(code_chunks)})",
                    "code_chunk": chunk,
                    "changed_blocks": review_query.get('changed_blocks', ''),
                    "surrounding_context": review_query.get('surrounding_context', ''),
                    "similar_codes": review_query.get('similar_codes', ''),
                    "branch": branch,
                    "mr_title": default_if_blank(mr_title, "Unavailable"),
                    "mr_description": default_if_blank(mr_description, "Unavailable")
                })

                file_codeReview_memory.save_context(
                    {"input": f"{file_path} (Part {i + 1}/{len(code_chunks)})"},
                    {"output": result}
                )

            except Exception as e:
                logger.info(f"청크 {i + 1} 처리 중 오류: {e}")
                continue

        # 리뷰 결과 통합
        if file_codeReview_memory:
            # 여러 리뷰 결과를 하나로 통합하는 프롬프트
            merge_prompt = ChatPromptTemplate.from_template("""
               다음은 하나의 파일에 대한 여러 부분의 코드리뷰 결과입니다.
               중복을 제거하고 실제 수정 가치가 있는 finding만 유지하세요.
               must_fix, should_fix, nit, positive 구분을 보존하세요.
               문제가 없다는 결론도 유지하세요.
    
               파일: {file_path}
               리뷰 결과들:
               {reviews}
           """)

            merge_chain = merge_prompt | llm | StrOutputParser()

            final_review = merge_chain.invoke({
                "file_path": file_path,
                "reviews": file_codeReview_memory.load_memory_variables({})[f"{project_id}_codereview_history_{uuid}"]
            })

            code_review_memory.save_context(
                {"input": f"{file_path}"},
                {"output": final_review}
            )

            return final_review
    except Exception as e:
        logger.info(f"코드리뷰 시 오류발생: {e}")
        return ''
    finally:
        file_codeReview_memory.clear()

    return "리뷰 결과가 없습니다."


def generate_uuid():
    return str(uuid.uuid4()).replace('-', '')


def generate_advice(mr_summaries):
    """
    MR Summaries 데이터를 기반으로 LLM을 활용해 종합적인 조언 생성.
    Args:
        mr_summaries (list): MR 요약 데이터 리스트
    Returns:
        str: 전체 MR 요약을 기반으로 한 종합 조언
    """

    if not isinstance(mr_summaries, list):
        raise ValueError("mr_summaries는 리스트여야 합니다.")

    if not mr_summaries:
        return "MR Summaries 데이터가 비어 있습니다. 검토할 요약이 없습니다."

    # LLM 초기화
    llm_model = LLMModel()
    llm = llm_model.llm

    try:
        # MR Summaries를 하나의 텍스트로 병합
        combined_summaries = "\n".join([f"- {summary}" for summary in mr_summaries])

        # LLM 프롬프트 생성
        prompt = f"""
        다음은 여러 Merge Request의 요약 리스트입니다. 이를 기반으로 전체 프로젝트의 기술적 상태와 개선 방향에 대한 조언 총 1문장으로 작성해주세요:

        Merge Request Summaries:
        {combined_summaries}

        작성 지침:
        - 전체 프로젝트의 기술적 상태와 개선 방향을 종합적으로 요약
        """

        # LLM 호출 - 올바른 타입(str) 전달
        response = llm(prompt)
        logger.info(f"조언 생성 결과: {response.content}")
        # 결과 반환 AIMessage
        return response.content

    except Exception as e:
        logger.info(f"LLM을 사용한 조언 생성 중 오류 발생: {e}")
        raise RuntimeError("조언 생성 실패") from e
