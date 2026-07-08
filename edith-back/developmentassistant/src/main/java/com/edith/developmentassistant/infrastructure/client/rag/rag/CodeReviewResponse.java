package com.edith.developmentassistant.infrastructure.client.rag.rag;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Builder
@Getter
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class CodeReviewResponse {

    private String review;
    private String status;
    private String summary;
    private List<CodeReviewFinding> findings;

    @JsonProperty("techStacks")
    private List<String> techStack;

    @Builder
    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class CodeReviewFinding {

        private String severity;
        private String category;
        private String file;
        private String line;
        private String issue;
        private String whyItMatters;
        private String suggestion;
        private List<String> evidence;
    }
}
