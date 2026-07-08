package com.edith.developmentassistant.infrastructure.client.rag.rag;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

class CodeReviewResponseTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void deserializesStructuredFindingsWithoutBreakingExistingFields() throws Exception {
        String json = """
                {
                  "status": "success",
                  "review": "<h3>Code Review</h3>",
                  "summary": "Auth review",
                  "techStacks": ["Java", "Spring"],
                  "findings": [
                    {
                      "severity": "must_fix",
                      "category": "auth",
                      "file": "UserController.java",
                      "line": "72",
                      "issue": "refresh does not update cookie",
                      "whyItMatters": "browser keeps using the expired cookie",
                      "suggestion": "set the new accessToken cookie",
                      "evidence": ["docs/review-rules/auth.md#Token Lifecycle"]
                    }
                  ]
                }
                """;

        CodeReviewResponse response = objectMapper.readValue(json, CodeReviewResponse.class);

        assertThat(response.getReview()).contains("Code Review");
        assertThat(response.getSummary()).isEqualTo("Auth review");
        assertThat(response.getTechStack()).containsExactly("Java", "Spring");
        assertThat(response.getFindings()).hasSize(1);
        assertThat(response.getFindings().get(0).getSeverity()).isEqualTo("must_fix");
        assertThat(response.getFindings().get(0).getEvidence())
                .containsExactly("docs/review-rules/auth.md#Token Lifecycle");
    }
}
