package com.edith.developmentassistant.infrastructure.client.rag.rag;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import org.junit.jupiter.api.Test;

class CodeReviewRequestTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void serializesMergeRequestContextWithExistingReviewPayload() throws Exception {
        CodeReviewRequest request = CodeReviewRequest.builder()
                .url("https://lab.ssafy.com")
                .token("token")
                .projectId("123")
                .mrIid("7")
                .branch("develop")
                .mrTitle("Fix refresh cookie")
                .mrDescription("Refresh should update the HttpOnly accessToken cookie.")
                .changes(List.of(CodeReviewChanges.builder()
                        .path("src/main/java/UserController.java")
                        .diff("@@ -1 +1 @@")
                        .build()))
                .build();

        JsonNode json = objectMapper.readTree(objectMapper.writeValueAsString(request));

        assertThat(json.get("url").asText()).isEqualTo("https://lab.ssafy.com");
        assertThat(json.get("projectId").asText()).isEqualTo("123");
        assertThat(json.get("mrIid").asText()).isEqualTo("7");
        assertThat(json.get("branch").asText()).isEqualTo("develop");
        assertThat(json.get("mrTitle").asText()).isEqualTo("Fix refresh cookie");
        assertThat(json.get("mrDescription").asText())
                .isEqualTo("Refresh should update the HttpOnly accessToken cookie.");
        assertThat(json.get("changes")).hasSize(1);
    }
}
