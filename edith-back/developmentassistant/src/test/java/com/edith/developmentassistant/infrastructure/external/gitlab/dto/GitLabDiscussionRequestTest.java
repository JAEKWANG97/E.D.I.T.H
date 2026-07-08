package com.edith.developmentassistant.infrastructure.external.gitlab.dto;

import static org.assertj.core.api.Assertions.assertThat;

import com.edith.developmentassistant.infrastructure.external.gitlab.dto.mergerequest.DiffRefs;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

class GitLabDiscussionRequestTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void serializesTextPositionForGitLabInlineDiscussion() throws Exception {
        DiffRefs diffRefs = new DiffRefs();
        diffRefs.setBaseSha("base");
        diffRefs.setStartSha("start");
        diffRefs.setHeadSha("head");

        GitLabDiscussionRequest request = GitLabDiscussionRequest.textPosition(
                "body",
                "src/main/java/UserController.java",
                72,
                diffRefs
        );

        JsonNode json = objectMapper.readTree(objectMapper.writeValueAsString(request));

        assertThat(json.get("body").asText()).isEqualTo("body");
        assertThat(json.get("position").get("position_type").asText()).isEqualTo("text");
        assertThat(json.get("position").get("base_sha").asText()).isEqualTo("base");
        assertThat(json.get("position").get("start_sha").asText()).isEqualTo("start");
        assertThat(json.get("position").get("head_sha").asText()).isEqualTo("head");
        assertThat(json.get("position").get("new_path").asText()).isEqualTo("src/main/java/UserController.java");
        assertThat(json.get("position").get("new_line").asInt()).isEqualTo(72);
    }
}
