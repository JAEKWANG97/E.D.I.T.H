package com.edith.developmentassistant.infrastructure.client.rag.rag;

import java.util.List;
import lombok.Builder;
import lombok.Getter;

@Builder
@Getter
public class CodeReviewRequest {
    String url;
    String token;
    String projectId;
    String mrIid;
    String branch;
    String mrTitle;
    String mrDescription;
    List<CodeReviewChanges> changes;
    List<String> techStacks;
}
