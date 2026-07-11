# E.D.I.T.H 프로젝트 기술 분석 및 포트폴리오 연계 가이드

## 1. 프로젝트 개요
- 프로젝트 한 줄 요약: GitLab 협업 데이터를 기반으로 AI 코드리뷰와 개인 포트폴리오를 자동 생성하고, 얼굴 벡터 기반 로그인까지 제공하는 마이크로서비스형 개발자 지원 플랫폼입니다.
- 어떤 문제를 해결하는 서비스인지: 팀 프로젝트에서 코드리뷰와 기여 정리는 반복적이고 비용이 큰 작업입니다. 이 프로젝트는 GitLab 프로젝트 등록, 웹훅 수신, MR diff 수집, AI 리뷰 생성, 리뷰 이력 저장, 포트폴리오 생성까지를 백엔드에서 자동화해 협업 부담을 줄이려는 구조를 갖고 있습니다. 별도 사용자 서비스와 얼굴 인식 서비스를 통해 로그인 경험도 분리했습니다.
- 백엔드 관점에서 이 프로젝트가 왜 의미 있는지: 단순 CRUD가 아니라 GitLab API, JWT/Redis 인증, Spring Cloud Gateway, Flask 기반 RAG, FastAPI 기반 얼굴 인식, Kubernetes 배포까지 이어지는 서비스 분리형 구조가 실제 코드로 확인됩니다. 특히 "웹훅 기반 이벤트 처리 → 외부 API 연동 → AI 서비스 호출 → 결과 저장/코멘트 등록" 흐름이 구현되어 있어 포트폴리오에서 설명할 수 있는 백엔드 깊이가 있습니다.

## 2. 백엔드 아키텍처 요약
- 서버 구성: `SCG`(8080), `user`(8081), `developmentassistant`(8082), `rag` Flask(8083), `face_recognition` FastAPI(8084)로 분리되어 있습니다. Spring Boot 3.3.5와 Java 17이 주 서버이고, AI·벡터 검색 관련 기능은 Python 서비스로 분리되어 있습니다.
- 저장소/캐시/메시징/외부 API: 운영 설정 기준으로 `user`와 `developmentassistant`는 MySQL을 사용하고, 두 서비스 모두 Redis를 사용합니다. 코드리뷰 RAG 서비스는 GraphCodeBERT 임베딩을 `Chroma`에 저장하고, 얼굴 인식 서비스는 `Qdrant`를 사용합니다. 외부 연동은 GitLab API, OpenAI API, 내부 서비스 간 HTTP 호출(RestTemplate/WebClient/httpx)입니다. 별도 메시지 브로커(Kafka/RabbitMQ)는 확인되지 않았고, 웹훅 처리는 동기 HTTP 요청 흐름입니다.
- 서비스 분리 여부와 책임: `user`는 회원가입/로그인/JWT 발급/refresh token 저장/얼굴 임베딩 등록 요청을 담당합니다. `developmentassistant`는 프로젝트 등록, GitLab 웹훅 처리, MR 요약 저장, 대시보드 집계, 포트폴리오 생성을 담당합니다. `SCG`는 라우팅과 일부 JWT 쿠키 검증을 담당하고, `rag`는 코드리뷰와 포트폴리오 생성을 수행하며, `face_recognition`은 Qdrant 기반 벡터 매칭 후 최종 로그인은 다시 `user` 서비스에 위임합니다.
- 배포/운영 방식: 서비스별 Dockerfile, Jenkinsfile, ECR 푸시, Kubernetes Deployment/Service YAML이 존재합니다. Jenkins 파이프라인은 빌드 후 ECR에 이미지를 푸시하고, 별도 YAML 저장소의 이미지 태그를 갱신하는 방식으로 동작합니다. K8s 매니페스트에는 replica, readiness/liveness probe, secret 주입, NodePort/ClusterIP 구성이 포함되어 있고, Nginx가 `/api`, `/ws`를 SCG로 프록시합니다.

## 3. 핵심 기술 분석
### A. GitLab 프로젝트 등록과 웹훅/토큰 온보딩 자동화
- 무엇을 구현했는지: 프로젝트 등록 시 사용자 토큰으로 GitLab 프로젝트 액세스 토큰을 생성하고, 해당 프로젝트에 웹훅을 자동 등록한 뒤, 서비스 내부 `Project`와 `UserProject`를 저장하는 흐름이 구현되어 있습니다.
- 왜 중요한지: 사용자가 프로젝트를 수동으로 여러 번 설정하지 않아도, 등록 직후부터 MR 이벤트를 자동 수집할 수 있는 구조가 됩니다. 외부 VCS를 플랫폼 내부 워크플로우로 끌어오는 핵심 진입점입니다.
- 코드 근거: `ProjectService.registerProject()`에서 사용자 정보 조회 후 `GitLabApi.generateProjectAccessToken()`과 `CodeReviewService.registerWebhook()`를 호출하고, `GitLabApi.registerWebhook()`은 GitLab `/projects/{id}/hooks`에 요청을 보냅니다. 관련 구현은 `ProjectService.java`, `GitLabApi.java`, `Project.java`, `UserProject.java`에 있습니다.

### B. 웹훅 기반 AI 코드리뷰 자동화 파이프라인
- 무엇을 구현했는지: GitLab 웹훅을 수신하면 MR diff, 최근 fix/refactor 로그, 최근 커밋 메시지, 최근 MR 요약을 수집하고, 이를 RAG 서비스에 전달해 코드리뷰를 생성한 뒤 GitLab MR 코멘트로 다시 등록합니다. 동시에 MR 요약을 DB에 저장하고 Redis 대시보드를 갱신합니다.
- 왜 중요한지: 단순 "AI 호출"이 아니라 소스 관리 이벤트를 받아 실제 리뷰 코멘트까지 남기는 자동화 루프가 구현되어 있습니다. 백엔드 이벤트 처리, 외부 API 호출, 저장소 갱신이 한 흐름으로 연결된다는 점이 포트폴리오 가치가 큽니다.
- 코드 근거: `WebhookController`가 `/api/v1/webhook`을 받고 `CodeReviewService.commentCodeReview()`를 호출합니다. 여기서 `fetchMergeRequestDiff()`, `fetchFilteredCommitMessages()`, `fetchRecentMRSummaries()`, `ragServiceClient.commentCodeReview()`, `mrSummaryRepository.save()`, `gitLabApi.addMergeRequestComment()`가 이어집니다. 관련 구현은 `WebhookController.java`, `CodeReviewService.java`, `GitLabApi.java`, `MRSummaryRepository.java`, `RagServiceClient.java`에 있습니다.

### C. 코드 특화 RAG와 포트폴리오 생성 파이프라인
- 무엇을 구현했는지: RAG 서비스는 GitLab 저장소를 clone한 뒤, Tree-sitter 기반 언어별 chunker로 함수/메서드 단위 코드를 분리하고, GraphCodeBERT 임베딩을 생성해 Chroma에 저장합니다. 리뷰 대상 diff의 추가 코드와 유사한 코드를 검색해 LLM 입력에 넣고, 생성된 리뷰를 다시 포트폴리오 요약과 최종 HTML 포트폴리오 생성에 활용합니다.
- 왜 중요한지: "변경 코드만 바로 LLM에 전달"하는 수준이 아니라, 코드 구조를 이해하는 전처리와 유사 코드 검색을 결합한 코드 특화 RAG 파이프라인이라는 점이 핵심입니다. 또한 포트폴리오 생성 쪽은 기존 MR summary와 GitLab MR diff를 함께 사용해 결과물을 누적형으로 구성합니다.
- 코드 근거: `GitLabCodeChunker`는 저장소 clone과 언어 판별/청킹을 담당하고, `java_chunking.py`, `python_chunking.py`, `javaScript_chunking.py`는 Tree-sitter 파서를 사용합니다. `CodeEmbeddingProcessor`는 Chroma 컬렉션을 만들고 GraphCodeBERT 임베딩을 저장합니다. `PortfolioService.getMergedMRs()`는 GitLab MR을 페이지 단위로 가져오고, `Flux.parallel()`로 diff를 병렬 조회합니다. 관련 구현은 `get_code.py`, `java_chunking.py`, `python_chunking.py`, `javaScript_chunking.py`, `embeddings.py`, `codebert_model.py`, `reviewer.py`, `portfolio.py`, `PortfolioService.java`에 있습니다.

### D. 인증, 사용자 정보 관리, 얼굴 인식 로그인 연동
- 무엇을 구현했는지: 이메일 로그인 시 JWT access/refresh token을 발급하고 refresh token은 Redis에 TTL과 함께 저장합니다. GitLab PAT는 회원가입 시 검증 후 암호화 저장하며, 로그인 시 복호화하여 GitLab 프로필을 조회합니다. 얼굴 로그인은 FastAPI가 Qdrant에서 가장 가까운 얼굴 벡터를 찾고, 최종 토큰 발급은 `user` 서비스가 수행합니다.
- 왜 중요한지: 인증 주체를 `user` 서비스에 집중하고, 얼굴 인식은 별도 서비스로 분리해 인증과 생체 매칭을 느슨하게 결합했습니다. 또한 HttpOnly/Secure 쿠키를 사용해 브라우저 토큰 보관 전략까지 포함되어 있습니다.
- 코드 근거: `UserService.signIn()`과 `refreshAccessToken()`은 JWT 발급/검증과 Redis 저장을 수행하고, `CookieUtil`은 `HttpOnly`, `Secure`, `SameSite=None` 쿠키를 설정합니다. `GitLabClient.validateAccessToken()`과 `fetchProfile()`은 GitLab API를 호출합니다. 얼굴 등록은 `FastAPIClient.registerFaceEmbedding()`, 얼굴 매칭은 `face_recognition.py`, Qdrant 저장은 `register_face_embedding.py`에 구현되어 있습니다.

### E. 서비스 게이트웨이와 역할 분리
- 무엇을 구현했는지: SCG가 `/api/v1/users/**`, `/api/v1/projects/**`, `/api/v1/portfolio/**`, `/api/v1/webhook/**`, `/api/v1/face-recognition/**`를 각 서비스로 라우팅하고, 일부 사용자 검증 엔드포인트에는 `JwtAuthFilter`를 적용합니다. Nginx는 `/api`와 `/ws`를 SCG로 프록시하고, 서비스별 K8s 매니페스트는 개별 replica와 service endpoint를 가집니다.
- 왜 중요한지: 인증/사용자, 프로젝트/리뷰/포트폴리오, AI RAG, 얼굴 인식이 기술 스택과 책임 기준으로 분리되어 있어 확장성과 운영 관점에서 설명하기 좋습니다. 특히 Java 서비스와 Python AI 서비스를 분리한 구조는 포트폴리오에서 "서비스 분리 이유"를 말하기에 적합합니다.
- 코드 근거: `SCG application-prod.yml`의 route 정의, `JwtAuthFilter.java`, `GatewayConfig.java`, `nginx_config_t3xlarge.yaml`, `user.yaml`, `developmentassistant.yaml`, `rag.yaml`, `face_recognition.yaml`, Jenkinsfile들이 이 구조를 뒷받침합니다.

## 4. 포트폴리오용 프로젝트 소개
E.D.I.T.H는 GitLab 협업 데이터를 활용해 AI 코드리뷰와 개인 포트폴리오를 자동 생성하는 개발자 지원 플랫폼입니다. 백엔드에서는 사용자 인증과 GitLab 토큰 관리, 프로젝트 등록과 웹훅 처리, MR 기반 리뷰 자동화, 포트폴리오 생성, 얼굴 벡터 로그인까지 여러 흐름이 서비스 단위로 분리되어 있습니다.

기술적으로는 Spring Boot 기반 비즈니스 서비스와 Python 기반 AI 서비스를 분리하고, GitLab API, Redis, MySQL, Chroma, Qdrant를 조합해 "외부 협업 도구와 내부 AI 파이프라인을 연결하는 백엔드"를 구현한 점이 핵심입니다. 단순 CRUD보다 이벤트 처리, 외부 연동, 인증, 배포 자동화 경험을 보여주기 좋은 프로젝트입니다.

## 5. 포트폴리오용 내 기여/기술적 의사결정
- GitLab 프로젝트 등록 시 액세스 토큰 발급과 웹훅 등록을 자동화해, 프로젝트 온보딩 이후 바로 리뷰 파이프라인이 동작하도록 설계했다는 점을 강조할 수 있습니다.
- MR 웹훅 수신 이후 diff 수집, AI 리뷰 요청, GitLab 코멘트 등록, MR summary 저장, Redis 대시보드 갱신까지를 하나의 백엔드 흐름으로 연결한 점을 기여 포인트로 설명할 수 있습니다.
- 인증은 `user` 서비스에 집중하고, SCG는 라우팅과 JWT 검증 일부만 담당하도록 역할을 분리한 점을 기술적 의사결정으로 설명할 수 있습니다.
- 얼굴 벡터 매칭은 FastAPI+Qdrant로 분리하고, 최종 access/refresh token 발급은 `user` 서비스가 담당하게 해 인증 책임을 한곳에 모은 구조를 설명할 수 있습니다.
- RAG 서비스는 Tree-sitter 기반 함수/메서드 단위 청킹과 GraphCodeBERT 임베딩을 사용해 "코드 구조를 고려한 검색형 AI 리뷰"를 시도한 점을 핵심 기술 포인트로 가져갈 수 있습니다.

## 6. 이력서에 쓸 수 있는 bullet 초안
- GitLab 프로젝트 등록, 프로젝트 액세스 토큰 발급, 웹훅 자동 등록, MR diff 수집, AI 코드리뷰 코멘트 등록까지 이어지는 협업 자동화 백엔드를 구현했습니다.
- Spring Boot(`user`, `developmentassistant`)·Spring Cloud Gateway·Flask RAG·FastAPI 얼굴 인식으로 분리된 서비스형 백엔드를 구축하고, JWT/Redis/Qdrant 기반 인증·인식 연동을 구현했습니다.
- Tree-sitter 기반 코드 청킹, GraphCodeBERT 임베딩, Chroma 유사 코드 검색, LangChain 기반 요약/포트폴리오 생성 파이프라인을 서비스에 통합했습니다.

## 7. 면접에서 강조할 기술 포인트
- GitLab 웹훅을 받은 뒤 어떤 데이터(diff, commit log, MR summary)를 수집하고 어디에 저장하며 어떻게 다시 GitLab 코멘트로 반영하는지 end-to-end 흐름을 설명할 수 있어야 합니다.
- 왜 AI 기능을 Spring 서비스 내부가 아니라 Flask/FastAPI 별도 서비스로 분리했는지, 기술 스택과 책임 분리 관점에서 설명하는 것이 좋습니다.
- Tree-sitter로 함수/메서드 단위 청킹을 한 이유와, 일반 텍스트 분할보다 코드 리뷰 품질에 어떤 차이를 주는지 설명하면 기술 깊이를 보여줄 수 있습니다.
- JWT access/refresh token을 Redis와 쿠키로 운영하는 구조, 그리고 gateway 검증과 내부 서비스 책임이 어떻게 나뉘는지 설명할 수 있어야 합니다.
- 얼굴 인식은 "벡터 매칭"만 수행하고 최종 인증 토큰은 user 서비스가 발급하는 구조라는 점을 말하면 인증 설계 의도를 설명하기 좋습니다.

## 8. 확인 필요 사항 / 과장 금지 포인트
- README에는 Qdrant, Anti-Spoofing, ArgoCD 등 폭넓은 설명이 있지만, 실제 코드로 직접 확인되는 코드리뷰 RAG 벡터 저장소는 `Chroma`입니다. Qdrant는 얼굴 인식 서비스에서 확인됩니다.
- Anti-Spoofing 로직은 inspected backend code에서 직접 확인되지 않았습니다. `deepface` 의존성은 있으나 라우터 코드에서는 실제 사용이 보이지 않으므로 핵심 주장으로 쓰면 과장입니다.
- GitLab 웹훅 URL은 `GitLabApi`에서 `https://edith-ai.xyz:30443/webhook`으로 하드코딩돼 있지만, Nginx 설정은 `/api`와 `/ws`만 SCG로 프록시하고, 컨트롤러 경로는 `/api/v1/webhook`입니다. 저장소 내부 설정만 보면 경로 일치 여부를 추가 확인해야 합니다.
- SCG WebSocket 경로는 `GatewayConfig`에 `/ws/v1/face-recognition/face_login`, `application-prod.yml`에는 `/ws/v1/face-recognition/face-login`으로 표기되어 있어 경로 불일치가 있습니다.
- `user` 서비스 `SecurityConfig`는 모든 요청을 `permitAll()`로 열어두고 있어, 실제 인증 강제는 쿠키 기반 토큰 파싱과 게이트웨이 필터에 많이 의존합니다. 내부망 전제 설계인지 확인이 필요합니다.
- `UserController.faceLogin()`은 refresh token 쿠키에 refresh token이 아니라 access token을 넣고 있습니다. 포트폴리오에서는 "구현" 사실로는 말할 수 있지만, 완성도 높은 인증 설계로 과장하면 위험합니다.
- `EncryptionUtil`의 AES 키는 코드에 하드코딩되어 있습니다. "민감정보 암호화 저장"은 말할 수 있지만, 운영 보안 모범사례 수준이라고 표현하면 과장입니다.
- 자동화 테스트는 현재 각 Spring 서비스의 `contextLoads()` 수준만 확인됩니다. 기능 테스트, 통합 테스트, 부하 테스트 근거는 저장소에서 확인되지 않습니다.
- RAG 응답 DTO는 `tech_stack` snake_case를 기대하지만 Flask 응답은 `techStacks`를 반환합니다. 실제 매핑 정상 동작 여부는 추가 확인이 필요합니다.

## 9. 참고한 핵심 파일
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/README.md`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/build.gradle`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/build.gradle`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/SCG/build.gradle`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/src/main/java/com/ssafy/edith/user/api/controller/UserController.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/src/main/java/com/ssafy/edith/user/api/service/UserService.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/src/main/java/com/ssafy/edith/user/util/JwtUtil.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/src/main/java/com/ssafy/edith/user/util/RedisUtil.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/src/main/java/com/ssafy/edith/user/util/CookieUtil.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/src/main/java/com/edith/developmentassistant/application/ProjectService.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/src/main/java/com/edith/developmentassistant/application/CodeReviewService.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/src/main/java/com/edith/developmentassistant/application/PortfolioService.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/src/main/java/com/edith/developmentassistant/interfaces/rest/WebhookController.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/src/main/java/com/edith/developmentassistant/infrastructure/external/gitlab/GitLabApi.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/src/main/java/com/edith/developmentassistant/infrastructure/client/rag/RagServiceClient.java`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/rag/flaskProject/app/services/reviewer.py`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/rag/flaskProject/app/services/portfolio.py`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/rag/flaskProject/app/chunking/get_code.py`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/face_recognition/routers/register_face_embedding.py`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/face_recognition/routers/face_recognition.py`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/SCG/src/main/resources/application-prod.yml`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/exec/docs/edith_eks_yaml/nginx/nginx_config_t3xlarge.yaml`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/user/Jenkinsfile`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/edith-back/developmentassistant/Jenkinsfile_eks`
- `/Users/yujaegwang/Documents/projects/E.D.I.T.H/exec/docs/edith_eks_yaml/scg/scg.yaml`
