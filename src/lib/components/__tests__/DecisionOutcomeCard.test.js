import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import DecisionOutcomeCard from "../DecisionOutcomeCard";

const baseDecision = {
  decision_state: "PROCEED",
  decision_valid: true,
  confidence_gate_passed: true,
  integrity_status: "CLEAN",
  decision_summary: "Behavioural evidence supports moving forward.",
  risk_summary: ["Watch for onboarding support needs."],
  evidence_summary: [
    {
      dimension: "ownership",
      evidence_summary: ["Set direction independently", "Closed execution gaps quickly"],
    },
  ],
  evidence_gaps: ["Need more evidence on ambiguity handling."],
  conflict_flags: ["Feedback signal mixed across examples."],
  conditions: ["Validate stakeholder management references."],
  trade_off_statement: "Strong ownership offsets narrower scope exposure.",
  rationale: "Behavioural evidence is consistent enough to proceed.",
  created_at: "2026-04-26T08:30:00Z",
};

function renderCard(props) {
  return renderToStaticMarkup(createElement(DecisionOutcomeCard, props));
}

describe("DecisionOutcomeCard", () => {
  it("renders the decision outcome card for a successful response", () => {
    const markup = renderCard({ status: "success", decision: baseDecision });

    expect(markup).toContain("Decision Outcome");
    expect(markup).toContain("Proceed");
    expect(markup).toContain("Confidence Validity");
    expect(markup).toContain("Integrity Status");
    expect(markup).toContain("Evidence Summary");
    expect(markup).toContain("Risk Summary");
    expect(markup).toContain("Evidence Gaps");
    expect(markup).toContain("Conditions");
    expect(markup).toContain("Trade-off");
    expect(markup).toContain("Rationale");
  });

  it("renders the PROCEED state label safely", () => {
    const markup = renderCard({
      status: "success",
      decision: { ...baseDecision, decision_state: "PROCEED" },
    });

    expect(markup).toContain("Proceed");
  });

  it("renders the PROCEED_WITH_CONDITIONS state label safely", () => {
    const markup = renderCard({
      status: "success",
      decision: { ...baseDecision, decision_state: "PROCEED_WITH_CONDITIONS" },
    });

    expect(markup).toContain("Proceed with Conditions");
  });

  it("renders the DO_NOT_PROCEED state label safely", () => {
    const markup = renderCard({
      status: "success",
      decision: { ...baseDecision, decision_state: "DO_NOT_PROCEED" },
    });

    expect(markup).toContain("Do Not Proceed");
  });

  it("renders the INSUFFICIENT_EVIDENCE state label safely", () => {
    const markup = renderCard({
      status: "success",
      decision: { ...baseDecision, decision_state: "INSUFFICIENT_EVIDENCE" },
    });

    expect(markup).toContain("Insufficient Evidence / No Judgement");
  });

  it("renders a neutral unavailable state", () => {
    const markup = renderCard({ status: "unavailable" });

    expect(markup).toContain("No behavioural decision outcome is available yet.");
  });

  it("renders a forbidden state message", () => {
    const markup = renderCard({ status: "forbidden" });

    expect(markup).toContain("You do not have access to this decision outcome.");
  });

  it("renders a generic load failure state", () => {
    const markup = renderCard({ status: "error" });

    expect(markup).toContain("Decision outcome could not be loaded.");
  });

  it("renders a loading state while the decision is being fetched", () => {
    const markup = renderCard({ status: "loading" });

    expect(markup).toContain("Loading decision outcome...");
  });

  it("does not render skills, ranking, or legacy pass fail language", () => {
    const markup = renderCard({
      status: "success",
      decision: {
        ...baseDecision,
        skills_score: 88,
        skills_outcome: "FAIL",
        match_score: 96,
        ranking: 1,
        best_candidate: true,
        audit_trace: "internal-only",
        legacy_label: "PASS",
        review_label: "REVIEW",
        title: "Skills Assessment Summary",
      },
    });
    const normalizedMarkup = markup.toLowerCase();

    expect(normalizedMarkup).not.toContain("skills assessment summary");
    expect(normalizedMarkup).not.toContain("skills_score");
    expect(normalizedMarkup).not.toContain("skills_outcome");
    expect(normalizedMarkup).not.toContain("match_score");
    expect(normalizedMarkup).not.toContain("ranking");
    expect(normalizedMarkup).not.toContain("best candidate");
    expect(normalizedMarkup).not.toContain("internal-only");
    expect(markup).not.toContain("PASS");
    expect(markup).not.toContain("REVIEW");
    expect(markup).not.toContain("FAIL");
  });
});
