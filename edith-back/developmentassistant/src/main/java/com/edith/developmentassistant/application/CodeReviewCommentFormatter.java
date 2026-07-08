package com.edith.developmentassistant.application;

import com.edith.developmentassistant.infrastructure.client.rag.rag.CodeReviewResponse;
import java.util.OptionalInt;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

class CodeReviewCommentFormatter {

    private static final Pattern LINE_REFERENCE = Pattern.compile("(?i)^lines?\\s+(\\d+)(?:\\s*-\\s*\\d+)?$");

    private CodeReviewCommentFormatter() {
    }

    static String formatReviewBody(CodeReviewResponse response) {
        return formatReviewBody(response.getFindings(), response.getReview());
    }

    static String formatReviewBody(List<CodeReviewResponse.CodeReviewFinding> findings, String fallbackReview) {
        if (findings == null || findings.isEmpty()) {
            return fallbackReview;
        }

        String blocking = renderFindings(findings.stream()
                .filter(CodeReviewCommentFormatter::isBlocking)
                .toList());
        String nonBlocking = renderFindings(findings.stream()
                .filter(finding -> !isBlocking(finding))
                .toList());

        StringBuilder body = new StringBuilder("### E.D.I.T.H Code Review Findings\n\n");
        if (!blocking.isBlank()) {
            body.append("#### Blocking / Action Required\n\n").append(blocking).append('\n');
        }
        if (!nonBlocking.isBlank()) {
            body.append("#### Non-blocking / Positive\n\n").append(nonBlocking).append('\n');
        }
        return body.toString().trim();
    }

    static String formatInlineBody(CodeReviewResponse.CodeReviewFinding finding) {
        return "**" + valueOrDefault(finding.getSeverity(), "finding") + "** "
                + valueOrDefault(finding.getIssue(), "No issue text")
                + "\n\nWhy: " + valueOrDefault(finding.getWhyItMatters(), "No impact provided")
                + "\n\nSuggestion: " + valueOrDefault(finding.getSuggestion(), "No suggestion provided")
                + "\n\nEvidence: " + renderEvidence(finding.getEvidence());
    }

    static OptionalInt parseNewLine(String line) {
        if (line == null) {
            return OptionalInt.empty();
        }
        String trimmed = line.trim();
        try {
            int value = Integer.parseInt(trimmed);
            return value > 0 ? OptionalInt.of(value) : OptionalInt.empty();
        } catch (NumberFormatException ignored) {
        }

        Matcher matcher = LINE_REFERENCE.matcher(trimmed);
        if (!matcher.matches()) {
            return OptionalInt.empty();
        }
        int value = Integer.parseInt(matcher.group(1));
        return value > 0 ? OptionalInt.of(value) : OptionalInt.empty();
    }

    private static boolean isBlocking(CodeReviewResponse.CodeReviewFinding finding) {
        return "must_fix".equals(finding.getSeverity()) || "should_fix".equals(finding.getSeverity());
    }

    private static String renderFindings(List<CodeReviewResponse.CodeReviewFinding> findings) {
        return findings.stream()
                .map(CodeReviewCommentFormatter::renderFinding)
                .collect(Collectors.joining("\n\n"));
    }

    private static String renderFinding(CodeReviewResponse.CodeReviewFinding finding) {
        String location = valueOrDefault(finding.getFile(), "unknown file")
                + ":" + valueOrDefault(finding.getLine(), "changed block");
        return "- **" + valueOrDefault(finding.getSeverity(), "finding") + "** "
                + "`" + location + "` "
                + valueOrDefault(finding.getIssue(), "No issue text")
                + "\n  - Why: " + valueOrDefault(finding.getWhyItMatters(), "No impact provided")
                + "\n  - Suggestion: " + valueOrDefault(finding.getSuggestion(), "No suggestion provided")
                + "\n  - Evidence: " + renderEvidence(finding.getEvidence());
    }

    private static String renderEvidence(List<String> evidence) {
        if (evidence == null || evidence.isEmpty()) {
            return "not provided";
        }
        return evidence.stream()
                .filter(item -> item != null && !item.isBlank())
                .collect(Collectors.joining(", "));
    }

    private static String valueOrDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }
}
