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

    @JsonProperty("techStacks")
    private List<String> techStack;
}
