package com.edith.developmentassistant.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.edith.developmentassistant.infrastructure.client.rag.rag.CodeReviewResponse;
import java.util.List;
import org.junit.jupiter.api.Test;

class CodeReviewCommentFormatterTest {

    @Test
    void formatsStructuredFindingsForMergeRequestComment() {
        CodeReviewResponse response = CodeReviewResponse.builder()
                .review("<h3>fallback</h3>")
                .findings(List.of(
                        CodeReviewResponse.CodeReviewFinding.builder()
                                .severity("must_fix")
                                .category("auth")
                                .file("UserController.java")
                                .line("72")
                                .issue("refresh does not update cookie")
                                .whyItMatters("browser keeps using the expired cookie")
                                .suggestion("set the new accessToken cookie")
                                .evidence(List.of("docs/review-rules/auth.md#Token Lifecycle"))
                                .build(),
                        CodeReviewResponse.CodeReviewFinding.builder()
                                .severity("positive")
                                .file("UserService.java")
                                .line("changed block")
                                .issue("clear transaction boundary")
                                .evidence(List.of("UserService.updateUser"))
                                .build()))
                .build();

        String body = CodeReviewCommentFormatter.formatReviewBody(response);

        assertThat(body).contains("Blocking / Action Required");
        assertThat(body).contains("Non-blocking / Positive");
        assertThat(body).contains("`UserController.java:72`");
        assertThat(body).contains("docs/review-rules/auth.md#Token Lifecycle");
        assertThat(body).doesNotContain("<h3>fallback</h3>");
    }

    @Test
    void fallsBackToRenderedReviewWhenFindingsAreEmpty() {
        CodeReviewResponse response = CodeReviewResponse.builder()
                .review("<h3>No finding</h3>")
                .findings(List.of())
                .build();

        assertThat(CodeReviewCommentFormatter.formatReviewBody(response)).isEqualTo("<h3>No finding</h3>");
    }

    @Test
    void formatsSingleInlineDiscussionBody() {
        CodeReviewResponse.CodeReviewFinding finding = CodeReviewResponse.CodeReviewFinding.builder()
                .severity("must_fix")
                .issue("refresh does not update cookie")
                .whyItMatters("browser keeps using the expired cookie")
                .suggestion("set the new accessToken cookie")
                .evidence(List.of("docs/api/user-auth.md#Endpoints"))
                .build();

        String body = CodeReviewCommentFormatter.formatInlineBody(finding);

        assertThat(body).contains("**must_fix** refresh does not update cookie");
        assertThat(body).contains("Suggestion: set the new accessToken cookie");
        assertThat(body).contains("docs/api/user-auth.md#Endpoints");
    }

    @Test
    void parsesOnlyConcreteNewLinesForInlineComments() {
        assertThat(CodeReviewCommentFormatter.parseNewLine("72")).hasValue(72);
        assertThat(CodeReviewCommentFormatter.parseNewLine("line 72")).hasValue(72);
        assertThat(CodeReviewCommentFormatter.parseNewLine("lines 72-75")).hasValue(72);
        assertThat(CodeReviewCommentFormatter.parseNewLine("changed block")).isEmpty();
        assertThat(CodeReviewCommentFormatter.parseNewLine("-1")).isEmpty();
    }
}
