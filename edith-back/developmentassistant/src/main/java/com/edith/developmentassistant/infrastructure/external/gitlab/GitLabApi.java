package com.edith.developmentassistant.infrastructure.external.gitlab;

import com.edith.developmentassistant.infrastructure.external.gitlab.dto.CommentRequest;
import com.edith.developmentassistant.infrastructure.external.gitlab.dto.GitMerge;

import com.edith.developmentassistant.infrastructure.external.gitlab.dto.ContributorDto;

import com.edith.developmentassistant.infrastructure.external.gitlab.dto.ProjectAccessTokenRequest;
import com.edith.developmentassistant.infrastructure.external.gitlab.dto.RegisterWebhookRequest;
import com.edith.developmentassistant.infrastructure.external.gitlab.dto.mergerequest.MergeRequestDiffResponse;
import com.edith.developmentassistant.infrastructure.external.gitlab.dto.GitCommit;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.List;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Service
@Slf4j
public class GitLabApi {

    private static final String GITLAB_API_URL = "https://lab.ssafy.com/api/v4";
    private static final String REGISTER_HOOK_ENDPOINT = "/projects/";
    private static final String MR_DIFF_ENDPOINT = "/projects/%d/merge_requests/%d/changes"; // DIFF 엔드포인트
    private static final String TOKEN_NAME = "E.D.I.T.H";

    @Value("${gitlab.webhook-url}")
    private String webhookUrl;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public GitLabApi(
            @Qualifier("gitLabRestTemplate")
            RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    public void registerWebhook(Long projectId, String personalAccessToken) {
        String url = GITLAB_API_URL + REGISTER_HOOK_ENDPOINT + projectId + "/hooks";

        RegisterWebhookRequest requestBody = createRequestBody();

        // 헤더 설정
        HttpHeaders headers = createHeader(personalAccessToken);
        HttpEntity<RegisterWebhookRequest> requestEntity = new HttpEntity<>(requestBody, headers);

        registerWebhook(projectId, url, requestBody, headers, requestEntity);
    }

    private void registerWebhook(Long projectId, String url, RegisterWebhookRequest requestBody, HttpHeaders headers,
                                 HttpEntity<RegisterWebhookRequest> requestEntity) {
        try {
            log.info("Registering webhook for project ID: {}", projectId);
            log.info("Request URL: {}", url);
            log.info("Request Body: {}", requestBody);
            log.info("Request Headers: {}", headers);
            ResponseEntity<Void> response = getVoidResponseEntity(projectId, url, requestEntity);

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Webhook registered successfully.");

            } else {
                log.error("Failed to register webhook. Status Code: {}", response.getStatusCode());
                throw new RuntimeException("Failed to register webhook");
            }
        } catch (Exception ex) {
            log.error("Error registering webhook: {}", ex.getMessage(), ex);
            throw ex;
        }
    }

    private ResponseEntity<Void> getVoidResponseEntity(Long projectId, String url,
                                                       HttpEntity<RegisterWebhookRequest> requestEntity) {
        ResponseEntity<Void> response = restTemplate.exchange(
                url,
                HttpMethod.POST,
                requestEntity,
                Void.class,
                projectId
        );
        return response;
    }

    private static HttpHeaders createHeader(String personalAccessToken) {
        HttpHeaders headers = new HttpHeaders();
        headers.set("PRIVATE-TOKEN", personalAccessToken);
        return headers;
    }

    public MergeRequestDiffResponse fetchMergeRequestDiff(Long projectId, Long mergeRequestIid,
                                                          String personalAccessToken) {
        String url = String.format(GITLAB_API_URL + MR_DIFF_ENDPOINT, projectId, mergeRequestIid);

        // 헤더 설정
        HttpHeaders headers = createHeader(personalAccessToken);
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Void> requestEntity = new HttpEntity<>(headers);

        try {
            log.info("Fetching MR DIFF for project ID: {} and MR IID: {}", projectId, mergeRequestIid);
            log.info("Request URL: {}", url);

            ResponseEntity<String> response = restTemplate.exchange(
                    url,
                    HttpMethod.GET,
                    requestEntity,
                    String.class
            );

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Fetched MR DIFF successfully.");
                log.info("Response Body: {}", response.getBody());
                return objectMapper.readValue(response.getBody(), MergeRequestDiffResponse.class);
            } else {
                log.error("Failed to fetch MR DIFF. Status Code: {}", response.getStatusCode());
                throw new RuntimeException("Failed to fetch MR DIFF");
            }
        } catch (Exception ex) {
            log.error("Error fetching MR DIFF: {}", ex.getMessage(), ex);
            throw new RuntimeException("Error fetching MR DIFF");
        }
    }

    public void addMergeRequestComment(Long projectId, Long mergeRequestIid, String token, String review,
                                       String summary) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/merge_requests/" + mergeRequestIid + "/notes";
        addCommnet(projectId, mergeRequestIid, token, summary, url);
        addCommnet(projectId, mergeRequestIid, token, review, url);

    }

    private void addCommnet(Long projectId, Long mergeRequestIid, String token, String review, String url) {
        // 리뷰 내용 설정
        CommentRequest commentRequest = new CommentRequest(review);

        // 헤더 설정
        HttpHeaders headers = createHeader(token);

        HttpEntity<CommentRequest> requestEntity = new HttpEntity<>(commentRequest, headers);

        try {
            log.info("Adding comment to MR ID {} in project {}: {}", mergeRequestIid, projectId, review);
            ResponseEntity<Void> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, Void.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Comment added successfully to MR.");
            } else {
                log.error("Failed to add comment. Status code: {}", response.getStatusCode());
            }
        } catch (Exception ex) {
            log.error("Error adding comment to MR: {}", ex.getMessage(), ex);
        }
    }

    public String generateProjectAccessToken(Long projectId, String token) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/access_tokens";

        // 헤더 설정
        HttpHeaders headers = createHeader(token);
        headers.setContentType(MediaType.APPLICATION_JSON);

        // 요청 본문 생성 (이름 및 모든 권한 설정 포함)

        log.info("Generating access token for project ID: {}", projectId);
        log.info("Request URL: {}", url);
        log.info("Request Headers: {}", headers);

        ProjectAccessTokenRequest projectAccessTokenRequest = ProjectAccessTokenRequest.builder()
                .name(TOKEN_NAME)
                .scopes(Arrays.asList(
                        "api",
                        "read_api",
                        "write_repository",
                        "read_repository"
                ))
                .expiresAt(LocalDate.now().plusYears(1)) // 현재 날짜로부터 1년 후
                .accessLevel(40)
                .build();

        log.info("Request Body: {}", projectAccessTokenRequest);
        try {
            log.info("Request Body: {}", objectMapper.writeValueAsString(projectAccessTokenRequest));
        } catch (JsonProcessingException e) {
            log.error("Error generating access token: {}", e.getMessage(), e);
        }

        HttpEntity<ProjectAccessTokenRequest> requestEntity = new HttpEntity<>(projectAccessTokenRequest, headers);

        try {
            log.info("Generating access token for project ID: {}", projectId);
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            if (response.getStatusCode() == HttpStatus.CREATED) {
                log.info("Access token generated successfully.");

                // JSON 파싱하여 access_token 추출
                JsonNode responseBody = objectMapper.readTree(response.getBody());
                String accessToken = responseBody.path("token").asText();

                log.info("Access token: {}", accessToken);
                return accessToken;
            } else {
                log.error("Failed to generate access token. Status code: {}", response.getStatusCode());
            }
        } catch (Exception ex) {
            log.error("Error generating access token: {}", ex.getMessage(), ex);
        }

        return null; // 실패 시 null 반환
    }


    public List<GitCommit> fetchCommitsInMergeRequest(Long projectId, Long mergeRequestIid, String projectAccessToken) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/merge_requests/" + mergeRequestIid + "/commits";

        HttpHeaders headers = createHeader(projectAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitCommit>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitCommit>>() {
                    });

            return response.getBody();
        } catch (RestClientException e) {
            log.error("Error fetching commits for merge request {} in project {}: {}", mergeRequestIid, projectId,
                    e.getMessage());
            throw e;
        }
    }

    public GitCommit fetchCommitDetails(Long projectId, String commitSha, String projectAccessToken) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/repository/commits/" + commitSha;
        HttpHeaders headers = createHeader(projectAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<GitCommit> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, GitCommit.class
            );

            return response.getBody();
        } catch (RestClientException e) {
            log.error("Error fetching GitLab commit details for commit {} in project {}: {}", commitSha, projectId,
                    e.getMessage());
            throw e;
        }
    }

    public List<ContributorDto> fetchContributors(Long projectId, String personalAccessToken) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/members";

        HttpHeaders headers = createHeader(personalAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<ContributorDto>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<ContributorDto>>() {
                    });

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Contributors fetched successfully for project ID: {}", projectId);
                try {
                    // response.getBody()를 JSON 문자열로 변환
                    String responseBodyJson = objectMapper.writeValueAsString(response.getBody());
                    log.info("Response Body: {}", responseBodyJson);
                } catch (JsonProcessingException e) {
                    log.error("Failed to convert response body to JSON", e);
                }
                return response.getBody();
            } else {
                log.error("Failed to fetch contributors. Status Code: {}", response.getStatusCode());
                throw new RuntimeException("Failed to fetch contributors");
            }
        } catch (RestClientException e) {
            log.error("Error fetching contributors for project {}: {}", projectId, e.getMessage());

            throw e;
        }
    }

    public List<GitMerge> fetchGitLabMergeRequests(Long projectId, String projectAccessToken) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/merge_requests?state=merged&per_page=5";

        HttpHeaders headers = createHeader(projectAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitMerge>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitMerge>>() {
                    });
            return response.getBody();
        } catch (RestClientException e) {
            log.error("Error fetching GitLab merge for project {}: {}", projectId, e.getMessage());
            throw e;
        }
    }

    private RegisterWebhookRequest createRequestBody() {
        return RegisterWebhookRequest.builder()
                .url(webhookUrl)
                .description("Development Assistant Webhook")
                .pushEvents(true)
                .tagPushEvents(true)
                .mergeRequestsEvents(true)
                .enableSslVerification(false)
                .pushEventsBranchFilter(null)
                .build();
    }

    public Integer fetchTodayUserCommitsCount(Long projectId, String projectAccessToken, String userEmail) {
        // 오늘 날짜 구하기
        String todayStart = LocalDate.now() + "T00:00:00Z";
        String todayEnd = LocalDate.now() + "T23:59:59Z";

        String url = GITLAB_API_URL + "/projects/" + projectId + "/repository/commits" +
                "?since=" + todayStart + "&until=" + todayEnd;

        HttpHeaders headers = createHeader(projectAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            // API 요청하여 커밋 리스트 가져오기
            ResponseEntity<List<GitCommit>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitCommit>>() {
                    }
            );

            List<GitCommit> todayCommits = response.getBody();
            assert todayCommits != null;

            int todayCommitsCount = (int) todayCommits.stream()
                    .filter(commit -> commit.getAuthor_email() != null) // Null 체크 추가
                    .filter(commit -> commit.getAuthor_email().equalsIgnoreCase(userEmail))
                    .count();

            log.info("Today's commits count for user {} in project {}: {}", userEmail, projectId, todayCommitsCount);

            return todayCommitsCount;
        } catch (RestClientException e) {
            log.error("Error fetching today's commits for user {} in project {}: {}", userEmail, projectId,
                    e.getMessage());
            throw e;
        }
    }

    public Integer fetchTodayUserMergeRequestsCount(Long projectId, String projectAccessToken, String userEmail) {
        // 오늘 날짜를 UTC 시간대로 설정
        String todayStart = LocalDate.now().atStartOfDay(ZoneOffset.UTC).toString();
        String todayEnd = LocalDate.now().atTime(23, 59, 59).atZone(ZoneOffset.UTC).toString();
        String username = getGitLabUserNameByToken(projectAccessToken);

        String url = GITLAB_API_URL + "/projects/" + projectId + "/merge_requests" +
                "?created_after=" + todayStart + "&created_before=" + todayEnd;

        HttpHeaders headers = createHeader(projectAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        log.info("Fetching today's merge requests from URL: {}", url);

        try {
            List<GitMerge> todayMerges = getGitMerges(url, entity);
            log.info("Today {} Merges : {}", userEmail, todayMerges);
            if (todayMerges == null || todayMerges.isEmpty()) {
                log.warn("No merge requests found for project {} between {} and {}", projectId, todayStart, todayEnd);
                return 0;
            }

            // 로그로 필터링 대상 확인
            todayMerges.forEach(mr -> log.info("Merge Request: {}, Author Email: {}",
                    mr, mr.getAuthor() != null ? mr.getAuthor().getName() : "null"));

            // 필터링: 작성자가 userEmail과 일치하는 Merge Request
            int todayMergeRequestsCount = (int) todayMerges.stream()
                    .filter(mr -> mr.getAuthor() != null && mr.getAuthor().getName() != null)
                    .filter(mr -> mr.getAuthor().getName().equalsIgnoreCase(username))
                    .count();

            log.info("Today's merge requests count for user {} in project {}: {}", userEmail, projectId,
                    todayMergeRequestsCount);

            return todayMergeRequestsCount;
        } catch (RestClientException e) {
            log.error("Error fetching today's merge requests for user {} in project {}: {}", userEmail, projectId,
                    e.getMessage());
            throw e;
        }
    }


    private List<GitMerge> getGitMerges(String url, HttpEntity<String> entity) {
        // API 요청하여 Merge Request 리스트 가져오기
        ResponseEntity<List<GitMerge>> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitMerge>>() {
                }
        );

        List<GitMerge> todayMerges = response.getBody();
        assert todayMerges != null;
        return todayMerges;
    }

    public Integer fetchMergeRequestsCount(Long id, String token) {
        String url = GITLAB_API_URL + "/projects/" + id + "/merge_requests";

        HttpHeaders headers = createHeader(token);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitMerge>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitMerge>>() {
                    });

            return response.getBody().size();
        } catch (RestClientException e) {
            log.error("Error fetching merge requests for project {}: {}", id, e.getMessage());
            throw e;
        }
    }

    public Integer fetchCommitsCount(Long id, String token) {
        String url = GITLAB_API_URL + "/projects/" + id + "/repository/commits?all=true";

        HttpHeaders headers = createHeader(token);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitCommit>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitCommit>>() {
                    });

            return response.getBody().size();
        } catch (RestClientException e) {
            log.error("Error fetching commits for project {}: {}", id, e.getMessage());
            throw e;
        }
    }

    public String fetchRecentCommitMessage(Long projectId, String token) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/repository/commits";

        HttpHeaders headers = createHeader(token);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitCommit>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitCommit>>() {
                    });
            log.info("Fetching recent commit message for project ID: {}", projectId);
            List<GitCommit> commits = response.getBody();
            assert commits != null;

            if (commits.isEmpty()) {
                return null;
            }

            log.info("Recent commit message: {}", commits.get(0).getMessage());

            return commits.get(0).getMessage();
        } catch (RestClientException e) {
            log.error("Error fetching recent commit message for project {}: {}", projectId, e.getMessage());
            throw e;
        }
    }

    public List<String> fetchFilteredCommitMessages(Long projectId, String token) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/repository/commits";

        HttpHeaders headers = createHeader(token);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitCommit>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitCommit>>() {
                    });

            List<GitCommit> commits = response.getBody();
            assert commits != null;

            // 필터링: 메시지가 fix, !HOTFIX, refactor로 시작하는 커밋만 반환
            return commits.stream()
                    .map(GitCommit::getMessage)
                    .filter(message -> message.startsWith("fix")
                            || message.startsWith("!HOTFIX")
                            || message.startsWith("refactor"))
                    .toList();

        } catch (RestClientException e) {
            log.error("Error fetching filtered commit messages for project {}: {}", projectId, e.getMessage());
            throw e;
        }
    }

    public Integer fetchTotalMergeRequestsCount(Long projectId, String token) {
        String url = GITLAB_API_URL + "/projects/" + projectId + "/merge_requests?state=merged";

        HttpHeaders headers = createHeader(token);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            log.info("Fetching total merged merge requests count for project ID: {}", projectId);

            // API 요청
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, entity, String.class);

            // 헤더에서 'X-Total' 값 추출
            String totalCountHeader = response.getHeaders().getFirst("X-Total");

            if (totalCountHeader != null) {
                int totalCount = Integer.parseInt(totalCountHeader);
                log.info("Total merged merge requests count: {}", totalCount);
                return totalCount;
            } else {
                log.warn("X-Total header not found in response for project ID: {}", projectId);
                return 0;
            }
        } catch (RestClientException e) {
            log.error("Error fetching total merged merge requests count for project {}: {}", projectId, e.getMessage());
            throw e;
        }
    }


    public Integer fetchTodayCommitsCount(Long projectId, String projectAccessToken) {
        String todayStart = LocalDate.now().atStartOfDay(ZoneOffset.UTC).toString();
        String todayEnd = LocalDate.now().atTime(23, 59, 59).atZone(ZoneOffset.UTC).toString();

        String url = GITLAB_API_URL + "/projects/" + projectId + "/repository/commits" +
                "?since=" + todayStart + "&until=" + todayEnd;

        HttpHeaders headers = createHeader(projectAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitCommit>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitCommit>>() {
                    }
            );

            List<GitCommit> todayCommits = response.getBody();
            assert todayCommits != null;

            int todayCommitsCount = todayCommits.size();
            log.info("Today's commits count for project {}: {}", projectId, todayCommitsCount);

            return todayCommitsCount;
        } catch (RestClientException e) {
            log.error("Error fetching today's commits for project {}: {}", projectId, e.getMessage());
            throw e;
        }
    }

    public Integer fetchTodayMergeRequestsCount(Long projectId, String personalAccessToken) {
        String todayStart = LocalDate.now().atStartOfDay(ZoneOffset.UTC).toString();
        String todayEnd = LocalDate.now().atTime(23, 59, 59).atZone(ZoneOffset.UTC).toString();

        String url = GITLAB_API_URL + "/projects/" + projectId + "/merge_requests" +
                "?created_after=" + todayStart + "&created_before=" + todayEnd;

        HttpHeaders headers = createHeader(personalAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<List<GitMerge>> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, new ParameterizedTypeReference<List<GitMerge>>() {
                    }
            );

            List<GitMerge> todayMergeRequests = response.getBody();
            assert todayMergeRequests != null;

            int todayMergeRequestsCount = todayMergeRequests.size();
            log.info("Today's merge requests count for project {}: {}", projectId, todayMergeRequestsCount);

            return todayMergeRequestsCount;
        } catch (RestClientException e) {
            log.error("Error fetching today's merge requests for project {}: {}", projectId, e.getMessage());
            throw e;
        }
    }

    private String getGitLabUserNameByToken(String personalAccessToken) {
        String url = GITLAB_API_URL + "/user";

        HttpHeaders headers = createHeader(personalAccessToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    url, HttpMethod.GET, entity, String.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                JsonNode rootNode = objectMapper.readTree(response.getBody());
                return rootNode.path("name").asText();
            } else {
                throw new RestClientException("Unexpected response status: " + response.getStatusCode());
            }
        } catch (RestClientException | IOException e) {
            log.error("Error fetching GitLab user name by token: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
