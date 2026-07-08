# 👓 E.D.I.T.H.
<img src="exec/readme_imgs/Thumnail.png" alt="Thumbnail" width="800"/>

## 🗓️ 프로젝트 개요

### 진행 기간

- 2024.10.14 ~ 2024.11.19 (6주)

### 팀 구성


| 이상민 | 이중현 | 김민주 | 유재광 | 신민경 | 주현민 |
| :--------------------------------------------------------------: | :--------------------------------------------------------------: | :--------------------------------------------------------------: | :--------------------------------------------------------------: | :-------------------------------------------------------------: | :-------------------------------------------------------------: |
| <img src="https://avatars.githubusercontent.com/u/134148399?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/98592001?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/87603324?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/65598179?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/82864501?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/156664061?v=4" width="100" height="100"> |
| Leader, BE | BE | Infra, BE | BE | FE | AI |

## 📢 서비스 소개

 **"E.D.I.T.H"** 는 개발자들이 GitLab을 활용한 협업 과정에서 발생하는 코드리뷰의 부담을 줄이고, 각 기여자가 무엇을 어떻게 기여했는지를 명확하게 정리해주는 포트폴리오를 자동으로 생성하는 것을 목표로 하고 있습니다. 또한 웹캠을 활용한 얼굴인식 기능을 통해 팀 내 작업자들이 비밀번호 없이 안전하게 로그인하고 프로젝트에 접근할 수 있게 합니다.

## 🥳 서비스 설계

### 기술 스택

|               | Front                                   | Back                                     | AI                       |
| ------------- | --------------------------------------- | ---------------------------------------- | ------------------------ |
| **Language**  |    JavaScript(ES6+), TypeScript        |            Java17                         |          python          |
| **IDE**       |       Visual Studio Code             |             IntelliJ                        |        Pycharm       |
| **Framework** |         React, Vite                   | Spring Boot | Pytorch, Tensorflow fastAPI, flask               |
| **Library**   | zustand, gitgraph, tailwind    ||  transformers, langchain, treesitter, openai |   

| DB           |               Infra              |     Monitoring       |        Tools         |
| :----------- |  :-----------------------------: | :------------------: | :------------------: |
| MySQL, Redis, Qdrant, ChromaDB | EKS, ECR, Jenkins, ArgoCD, Nginx, Docker, Mattermost |Grafana, Grafana-Loki, promtail| GitLab, Jira, Notion, MatterMost |

### ERD

![ERD](./exec/readme_imgs/erd.png)

### Wireframe

[📎 Figma Link](https://www.figma.com/design/gtZSlKBrvWnMwKEhw8YoFp/SSAFY%EC%9E%90%EC%9C%A8?node-id=0-1&t=otipj6NdPiacAX1B-1)

![화면설계](./exec/readme_imgs/wireframe.png)

### Architecture

![아키텍쳐 구성도](./exec/readme_imgs/architecture.png)

### Docs

[📎 API](https://gwenportfolio.notion.site/API-11fbdf75de3b81bab422d837e660b95a?pvs=4)  
[📎 기능 정의서](https://gwenportfolio.notion.site/11fbdf75de3b81a49411f0891770769c?pvs=4)

## 🤗 기능 소개

### 1. 메인 화면
- 회원가입, 로그인 제공
  - 이메일 로그인, 얼굴인식 로그인 선택
  
![main.png](./exec/docs/imgs/main.png)

### 2. 회원 가입
- 이메일, 비밀번호, Git Personal Access Token 입력

![signup.png](./exec/docs/imgs/signup.png)
![signup.png](./exec/docs/imgs/signup_success.png)



### 4. 사용자 화면 입장
- 사용자의 프로젝트, 사용자 당일 커밋 수, 사용자 당일 MR 요청 수 제공 
  
![signup_success.png](./exec/docs/imgs/signin_success.png)

### 5. 프로젝트 등록
- GitLab repository의 project ID, 프로젝트 이름, 코드리뷰 대상 branch, 설명을 입력하여 진행중인 프로젝트를 등록

![project_register.png](./exec/docs/imgs/project_register.png)
![project_register_success.png](./exec/docs/imgs/project_register_success.png)

- 등록에 성공할 경우 해당 gitlab repository에 webhook 자동 생성
  
![webhook.png](./exec/docs/imgs/webhook.png)

### 6. 코드리뷰
- 프로젝트를 진행하며 MR 등록을 했을 때, 일정 시간 후 AI 코드리뷰 등록

![mr.png](./exec/docs/imgs/mr.png)
![code_review.png](./exec/docs/imgs/code_review.png)

### 7. 프로젝트 대시보드 확인
- 프로젝트에 대한 전체적인 정보 제공

![project_info.png](./exec/docs/imgs/project_info.png)

### 8. 개인 포트폴리오 생성
- 나의 포트폴리오 생성 버튼을 누를 경우 다음과 같은 AI 기반의 개인 맞춤형 포트폴리오 제공

![portfolio.png](./exec/docs/imgs/portfolio.png)

## 🚩핵심 기능

### 1. RAG를 활용한 LLM 기반 자동 코드리뷰
- **기능 설명**:
  - **GitLab MR 감지**: GitLab Webhook을 통해 MR 이벤트를 수신하면, 프로젝트 ID, MR IID, 대상 브랜치, MR 제목/설명, 변경 파일 diff를 수집합니다.
  - **변경 유형 분류**: MR 제목, 설명, target branch, 변경 파일 경로, diff 내용을 기반으로 `auth`, `api-contract`, `async`, `security`, `persistence`, `operations`, `rag-review`, `testing` 등 리뷰 카테고리와 위험도를 분류합니다.
  - **Code RAG**: 프로젝트 코드를 tree-sitter로 함수/메서드 단위 chunking한 뒤 GraphCodeBERT 기반 embedding으로 검색합니다. 각 코드 chunk에는 파일 경로, 모듈, 언어, 클래스명, 메서드명, annotation, symbol, AST symbol, category hint, content metadata를 함께 저장합니다.
  - **검색 결과 재정렬**: embedding 유사도만 사용하지 않고 같은 파일, 같은 모듈 경로, 같은 category, symbol overlap, tree-sitter AST symbol overlap, class match 여부를 기준으로 관련 코드를 reranking합니다. 선택된 코드 evidence에는 `same category`, `symbol overlap`, `ast symbol overlap` 같은 선택 이유를 남깁니다.
  - **Document RAG**: 코드뿐 아니라 프로젝트 문서도 리뷰 근거로 활용합니다. `docs/review-rules`, `docs/api`, `docs/adr`, `docs/architecture` 문서를 heading 단위로 chunking하고, 변경 유형에 맞는 review rule, API contract, ADR, architecture 문서를 검색합니다.
  - **Evidence Pack 생성**: LLM에 raw diff만 넘기지 않고 `Change`, `Classification`, `Changed Code`, `Related Code`, `Project Rule Evidence`, `API Contract Evidence`, `Architecture Decision Evidence`, `Historical Review Findings`로 구성된 Evidence Pack을 제공합니다.
  - **Structured Findings 생성**: LLM은 HTML 문자열이 아니라 `severity`, `category`, `file`, `line`, `issue`, `whyItMatters`, `suggestion`, `evidence`를 포함한 structured findings JSON을 생성합니다. 기존 클라이언트 호환을 위해 `review`, `summary`, `techStacks` 응답도 유지합니다.
  - **GitLab 리뷰 등록**: file과 line이 명확한 finding은 GitLab inline discussion으로 등록하고, line mapping이 어려운 항목은 MR-wide comment로 fallback합니다. blocking finding과 non-blocking/positive finding을 분리해 리뷰 품질을 높입니다.
  - **Review Memory 활용**: 생성된 finding은 projectId, mrId, category, severity, file, line, issue, suggestion, evidence, status와 함께 저장됩니다. 이후 유사한 변경이 발생하면 과거 finding을 historical evidence로 검색하며, `falsePositive`로 표시된 finding은 재사용하지 않습니다.

- **코드리뷰 파이프라인**:

```text
GitLab Webhook
→ Change Extractor
→ Change Classifier
→ Evidence Router
→ Code RAG / Document RAG / Review Memory
→ Evidence Pack
→ Review LLM
→ Structured Findings JSON
→ GitLab Inline Discussion / MR Comment
→ Review Memory
```

- **리뷰 결과 예시**:

```json
{
  "findings": [
    {
      "severity": "must_fix",
      "category": "auth",
      "file": "UserController.java",
      "line": "72",
      "issue": "Refresh token flow does not update the access token cookie.",
      "whyItMatters": "HttpOnly cookie 기반 브라우저 클라이언트는 직접 토큰을 갱신할 수 없어 세션이 끊길 수 있습니다.",
      "suggestion": "새 access token을 CookieUtil.addAccessToken으로 다시 내려주세요.",
      "evidence": [
        "docs/api/user-auth.md#Endpoints",
        "CookieUtil.addAccessToken"
      ]
    }
  ],
  "summary": "인증 흐름의 cookie 갱신 정책을 확인해야 합니다.",
  "techStacks": ["Java", "Spring"]
}
```

### 2. 포트폴리오 생성
- **기능 설명**:
    - **자동 분석**: 각 커밋에 대한 코드 리뷰 기록을 바탕으로, 기여자가 프로젝트에 어떤 영향을 미쳤는지를 자동으로 분석합니다. 트러블슈팅, 추가된 기능, 코드 개선 사항 등을 정리하여 포트폴리오를 구성합니다.
    - **트러블슈팅 기록**: 기여자가 해결한 문제에 대한 로그를 자동으로 추적하고, 이를 상세하게 기록하여 포트폴리오의 문제 해결 섹션에 포함시킵니다.
    - **핵심 기능 분석**: 기여자가 프로젝트에서 개발한 주요 기능을 식별하여, 포트폴리오에 해당 기여자가 맡은 기능과 성과를 명확하게 표시합니다.
    - **기여자별 분류**: 각 기여자가 담당한 코드와 모듈을 분류하고, 팀 프로젝트에서의 기여도와 역할을 정리하여 포트폴리오에 반영합니다.
- **포트폴리오 구성 요소**:
    - **트러블슈팅 기록**: 프로젝트 중 발생한 문제점과 그 해결 과정.
    - **핵심 기능**: 기여자가 개발한 주요 기능 및 기여한 코드 영역.
    - **기여자별 담당 기능**: 프로젝트에서 각 기여자가 담당한 모듈, 기능 등을 분류하여 정리.

### 3. 얼굴 인식 로그인

- **보안**: 얼굴 인식 데이터는 안전하게 처리되고 저장됩니다. 실시간으로 인식을 수행하여 편리하면서도 보안성이 높은 환경을 제공합니다.
얼굴 벡터 데이터는 Qdrant를 활용해 유사도를 계산하고, Anti-Spoofing 기술을 적용하여 보안성을 강화했습니다.

- **기능 설명**: 웹캠을 이용한 얼굴 인식 시스템을 통해 사용자들이 비밀번호 없이 안전하게 프로젝트 시스템에 로그인/로그아웃 할 수 있습니다.
  - 얼굴 데이터 전처리
  사용자가 입력한 얼굴 이미지를 클라이언트(React)에서 전처리 후, 벡터 데이터로 변환.
  변환된 벡터 데이터만 서버로 전송하여 개인 데이터를 보호.
  - Anti-Spoofing 기술 적용
  사용자가 업로드한 얼굴 이미지를 분석해 실제 사용자와의 일치 여부를 판단.
  사진이나 동영상 등으로 로그인 시도를 방지하여 보안 강화.
  - 벡터 데이터 비교 (Qdrant 사용)
  Qdrant의 벡터 데이터베이스를 사용하여 사용자의 얼굴 벡터와 기존 데이터 간 유사도를 계산.
  유클리드 거리 계산(Euclidean Distance) 알고리즘을 사용하여 벡터 간의 거리를 측정하고, 사전 정의된 임계값을 기준으로 인증 여부 결정.
