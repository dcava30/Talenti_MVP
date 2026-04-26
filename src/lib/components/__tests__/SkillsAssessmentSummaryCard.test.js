import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import SkillsAssessmentSummaryCard from "../SkillsAssessmentSummaryCard";

const baseSummary = {
  observed_competencies: [
    {
      competency: "Discovery",
      evidence_strength: "MEDIUM",
      confidence: "HIGH",
      source_references: ["resume", "transcript segment 12"],
    },
  ],
  competency_coverage: {
    coverage_band: "partial",
    required: 5,
    observed: 3,
    required_competencies_observed: ["Discovery", "Stakeholder management"],
  },
  skill_gaps: ["Forecasting depth"],
  evidence_strength: "MEDIUM",
  confidence: "HIGH",
  source_references: [
    {
      source: "model-service-2",
      artifact_type: "skills_assessment_summary",
      reference_id: "skills-ref-1",
    },
  ],
  human_readable_summary: "Organisational skills evidence is available for recruiters.",
  requires_human_review: true,
  model_version: "ms2-shadow-v1",
  created_at: "2026-04-26T08:30:00Z",
};

function renderCard(props) {
  return renderToStaticMarkup(createElement(SkillsAssessmentSummaryCard, props));
}

describe("SkillsAssessmentSummaryCard", () => {
  it("renders the skills assessment summary card for a successful response", () => {
    const markup = renderCard({ status: "success", summary: baseSummary });

    expect(markup).toContain("Skills Assessment Summary");
    expect(markup).toContain("This summary is not used in the behavioural TDS decision outcome.");
    expect(markup).toContain("Observed Skills Evidence");
    expect(markup).toContain("Competency Coverage");
    expect(markup).toContain("Skills Gaps");
    expect(markup).toContain("Evidence Strength");
    expect(markup).toContain("Requires Human Review");
    expect(markup).toContain("Source References");
    expect(markup).toContain("Discovery");
    expect(markup).toContain("Forecasting depth");
    expect(markup).toContain("ms2-shadow-v1");
  });

  it("renders a neutral unavailable state", () => {
    const markup = renderCard({ status: "unavailable" });

    expect(markup).toContain("No Skills Assessment Summary is available yet.");
  });

  it("renders an access denied state", () => {
    const markup = renderCard({ status: "forbidden" });

    expect(markup).toContain("You do not have access to this Skills Assessment Summary.");
  });

  it("renders a generic load failure state", () => {
    const markup = renderCard({ status: "error" });

    expect(markup).toContain("Skills Assessment Summary could not be loaded.");
  });

  it("renders a loading state while the summary is being fetched", () => {
    const markup = renderCard({ status: "loading" });

    expect(markup).toContain("Loading Skills Assessment Summary...");
  });

  it("does not render behavioural decision, ranking, or pass fail outcome language", () => {
    const markup = renderCard({
      status: "success",
      summary: {
        ...baseSummary,
        decision_state: "PROCEED",
        decision_valid: true,
        confidence_gate_passed: true,
        integrity_status: "CLEAN",
        risk_stack: ["escalation"],
        behavioural_rationale: "Behavioural rationale text",
        match_score: 98,
        ranking: 1,
        best_candidate: true,
        skills_fit_score: 91,
        human_readable_summary: "PASS REVIEW FAIL Proceed Do Not Proceed Insufficient Evidence best candidate skills fit score.",
        source_references: [
          {
            source: "model-service-2",
            ranking: 1,
            match_score: 91,
            raw_hiring_label: "PASS",
            raw_review_marker: "REVIEW",
            raw_fail_marker: "FAIL",
          },
        ],
      },
    });
    const normalizedMarkup = markup.toLowerCase();

    expect(normalizedMarkup).not.toContain(">decision outcome<");
    expect(normalizedMarkup).not.toContain("decision_state");
    expect(normalizedMarkup).not.toContain("proceed");
    expect(normalizedMarkup).not.toContain("do not proceed");
    expect(normalizedMarkup).not.toContain("insufficient evidence");
    expect(normalizedMarkup).not.toContain("risk_stack");
    expect(normalizedMarkup).not.toContain("behavioural rationale");
    expect(normalizedMarkup).not.toContain("match_score");
    expect(normalizedMarkup).not.toContain("ranking");
    expect(normalizedMarkup).not.toContain("best candidate");
    expect(normalizedMarkup).not.toContain("skills fit score");
    expect(markup).not.toContain("PASS");
    expect(markup).not.toContain("FAIL");
  });

  it("only uses the word review in the safe requires human review label", () => {
    const markup = renderCard({
      status: "success",
      summary: {
        ...baseSummary,
        human_readable_summary: "REVIEW evidence says more checking is needed.",
      },
    });
    const normalizedMarkup = markup.toLowerCase();
    const reviewMatches = normalizedMarkup.match(/review/g) ?? [];

    expect(markup).toContain("Requires Human Review");
    expect(reviewMatches).toHaveLength(1);
  });
});
