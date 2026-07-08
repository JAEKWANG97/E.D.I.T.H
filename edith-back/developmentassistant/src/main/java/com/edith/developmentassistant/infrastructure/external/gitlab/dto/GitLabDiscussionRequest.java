package com.edith.developmentassistant.infrastructure.external.gitlab.dto;

import com.edith.developmentassistant.infrastructure.external.gitlab.dto.mergerequest.DiffRefs;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class GitLabDiscussionRequest {

    private String body;
    private Position position;

    public static GitLabDiscussionRequest textPosition(String body, String path, int newLine, DiffRefs diffRefs) {
        return new GitLabDiscussionRequest(body, Position.text(path, newLine, diffRefs));
    }

    @Getter
    @AllArgsConstructor
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public static class Position {
        private String positionType;
        private String baseSha;
        private String startSha;
        private String headSha;
        private String newPath;
        private Integer newLine;

        static Position text(String path, int newLine, DiffRefs diffRefs) {
            return new Position(
                    "text",
                    diffRefs.getBaseSha(),
                    diffRefs.getStartSha(),
                    diffRefs.getHeadSha(),
                    path,
                    newLine
            );
        }
    }
}
