# E.D.I.T.H

Evidence-grounded AI code review assistant for GitLab merge requests.

E.D.I.T.H는 GitLab MR이 열렸을 때 변경 diff만 요약하는 도구가 아니라, 변경 코드와 관련 코드, 프로젝트 문서, API 계약, ADR, 과거 리뷰 이력을 함께 검색해 근거 기반 코드리뷰를 생성하는 시스템입니다.

기존 기능에는 프로젝트 대시보드, 포트폴리오 생성, 얼굴 인식 로그인도 포함되어 있지만, 이 README는 핵심 기능인 자동 코드리뷰 파이프라인을 기준으로 설명합니다.

## Problem

일반적인 LLM 코드리뷰는 다음 문제가 있습니다.

- diff만 보고 리뷰해서 프로젝트 규칙과 API 계약을 놓친다.
- 비슷한 코드를 검색하더라도 왜 그 코드가 근거인지 설명하지 못한다.
- 리뷰 결과가 HTML 문자열에 갇혀 inline comment, 재사용, 품질 측정으로 확장하기 어렵다.
- 과거에 지적했던 결함이나 false positive 이력이 다음 리뷰에 반영되지 않는다.

E.D.I.T.H의 목표는 리뷰 결과를 "LLM 의견"이 아니라 "검색된 근거에 기반한 structured finding"으로 만드는 것입니다.

## Review Pipeline

```text
GitLab Webhook
-> Change Extractor
-> Change Classifier
-> Evidence Router
-> Code RAG / Document RAG / Review Memory
-> Evidence Pack
-> Review LLM
-> Structured Findings JSON
-> GitLab Inline Discussion / MR Comment
-> Review Memory
```

## Core Capabilities

### 1. Change Classification

MR title, description, target branch, changed file paths, diff content를 기준으로 리뷰 카테고리와 위험도를 분류합니다.

현재 분류 카테고리:

- `auth`
- `api-contract`
- `async`
- `security`
- `persistence`
- `operations`
- `rag-review`
- `testing`

분류 결과는 Evidence Router의 입력으로 사용됩니다. 예를 들어 `auth`와 `api-contract`가 잡히면 JWT/Cookie 관련 코드, auth review rule, API contract 문서, 관련 ADR을 우선 검색합니다.

### 2. Code RAG with GraphCodeBERT

코드 검색에는 GraphCodeBERT 기반 embedding 경로를 유지합니다.

코드 chunk는 단순 텍스트가 아니라 다음 metadata를 함께 가집니다.

- `path`
- `module`
- `language`
- `kind`
- `className`
- `methodName`
- `annotations`
- `symbols`
- `categoryHints`
- `content`

검색 결과는 embedding score만으로 쓰지 않고, 같은 파일, 같은 모듈 경로, category match, symbol overlap, class match를 기준으로 reranking합니다. 각 related code evidence에는 왜 선택됐는지 `reason`이 포함됩니다.

### 3. Document RAG

자연어 문서는 GraphCodeBERT에 억지로 태우지 않고 별도의 text/document retrieval 경로로 검색합니다.

문서 evidence는 heading 단위로 chunking되며 front matter metadata를 사용합니다.

```yaml
id: api-rag-code-review
type: api-contract
category: rag-review
applies_to:
  - /rag/code-review
  - CodeReviewRequest
  - CodeReviewResponse
risk:
  - compatibility
```

문서 구조:

```text
docs/
  review-rules/
    auth.md
    api-contract.md
    async.md
    security.md
    testing.md
    rag-review.md
  adr/
    auth-token-policy.md
    rag-code-review-pipeline.md
    async-webhook-processing.md
  api/
    user-auth.md
    rag-code-review.md
    gitlab-webhook.md
  architecture/
    backend-services.md
    rag-pipeline.md
```

Evidence Pack에는 문서 evidence가 타입별로 분리됩니다.

- `Project Rule Evidence`
- `API Contract Evidence`
- `Architecture Decision Evidence`

### 4. Evidence Pack Prompting

LLM에는 raw diff만 넘기지 않습니다. 파일별 Evidence Pack을 구성해 "무엇을 근거로 리뷰해야 하는지"를 명시합니다.

Evidence Pack sections:

- `Change`
- `Classification`
- `Changed Code`
- `Related Code / Similar Implementations`
- `Project Rule Evidence`
- `API Contract Evidence`
- `Architecture Decision Evidence`
- `Historical Review Findings`

리뷰 프롬프트는 다음 원칙을 강제합니다.

- 근거 없는 finding을 만들지 않는다.
- 변경사항을 길게 요약하지 않는다.
- 실제 버그, 회귀 위험, 보안 문제, 계약 위반, 테스트 누락을 우선한다.
- 각 finding은 evidence reference를 포함한다.
- 문제가 없으면 findings를 비운다.

### 5. Structured Findings JSON

리뷰 결과의 원본은 HTML이 아니라 structured JSON입니다.

```json
{
  "findings": [
    {
      "severity": "must_fix",
      "category": "auth",
      "file": "UserController.java",
      "line": "72",
      "issue": "Refresh token flow does not update the access token cookie.",
      "whyItMatters": "Browser clients using HttpOnly cookies cannot keep the session valid.",
      "suggestion": "Write the new access token through CookieUtil.addAccessToken.",
      "evidence": [
        "docs/api/user-auth.md#Endpoints",
        "CookieUtil.addAccessToken"
      ]
    }
  ],
  "summary": "Auth review summary",
  "techStacks": ["Java", "Spring"]
}
```

기존 Java client 호환성을 위해 `review`, `summary`, `techStacks` 응답은 유지합니다. `review`는 structured findings에서 렌더링되는 표현입니다.

### 6. GitLab Review Output

structured finding은 GitLab comment에 맞게 두 경로로 출력됩니다.

- `file`과 숫자 `line`이 있는 finding: GitLab inline discussion 시도
- line mapping이 불가능하거나 실패한 finding: MR-wide comment fallback

blocking finding과 non-blocking/positive finding은 MR-wide fallback에서도 분리해 표시됩니다.

### 7. Review Memory

생성된 finding은 Review Memory에 저장됩니다.

저장 필드:

- `findingId`
- `projectId`
- `mrId`
- `category`
- `severity`
- `file`
- `line`
- `issue`
- `suggestion`
- `evidence`
- `status`

지원 status:

- `generated`
- `accepted`
- `resolved`
- `falsePositive`

다음 리뷰에서는 같은 project/file/category, issue overlap, status를 기준으로 historical finding을 evidence로 검색합니다. `falsePositive`로 표시된 finding은 재사용하지 않습니다.

## Key Code Paths

```text
edith-back/developmentassistant/
  src/main/java/com/edith/developmentassistant/application/CodeReviewService.java
  src/main/java/com/edith/developmentassistant/application/CodeReviewCommentFormatter.java
  src/main/java/com/edith/developmentassistant/infrastructure/client/rag/rag/
  src/main/java/com/edith/developmentassistant/infrastructure/external/gitlab/GitLabApi.java

edith-back/rag/flaskProject/
  app/routes/routes.py
  app/services/reviewer.py
  app/services/document_rag.py
  app/services/code_metadata.py
  app/services/embeddings.py
  app/services/review_output.py
  app/services/review_memory.py
```

## APIs

### RAG Code Review

```http
POST /rag/code-review
```

Input includes GitLab project context, MR metadata, target branch, changed files, and optional MR IID.

Output:

- `status`
- `review`
- `summary`
- `techStacks`
- `findings`

### Review Memory Status

```http
POST /rag/review-memory/status
```

Used to update whether a finding was accepted, resolved, or false positive.

```json
{
  "projectId": "123",
  "mrId": "7",
  "findingId": "abc123",
  "status": "falsePositive"
}
```

## Validation

Python RAG validation:

```bash
python3 -m py_compile \
  edith-back/rag/flaskProject/app/services/document_rag.py \
  edith-back/rag/flaskProject/app/services/code_metadata.py \
  edith-back/rag/flaskProject/app/services/review_output.py \
  edith-back/rag/flaskProject/app/services/review_memory.py \
  edith-back/rag/flaskProject/app/services/reviewer.py

python3 -m unittest discover edith-back/rag/flaskProject/tests
```

Java client/GitLab integration validation:

```bash
cd edith-back/developmentassistant
sh gradlew test
```

Current focused test coverage includes:

- markdown front matter and heading chunking
- category and target branch classification
- document retrieval for review rules, API contracts, ADRs, architecture docs
- code metadata extraction for Java, Python, JavaScript
- metadata-aware code reranking with evidence reasons
- structured JSON parsing and HTML rendering fallback
- Review Memory persistence, deduplication, retrieval, status updates
- GitLab inline discussion request serialization
- Java RAG request/response compatibility

## Supporting Features

E.D.I.T.H also includes:

- project registration and GitLab webhook registration
- project dashboard
- AI-assisted portfolio summary generation
- face-recognition login flow

These features support the broader product, but the main technical focus of this repository is the evidence-grounded code review pipeline.
