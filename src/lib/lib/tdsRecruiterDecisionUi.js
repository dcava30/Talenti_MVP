import { interviewsApi } from "@/api/interviews";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

export function isTdsRecruiterDecisionUiEnabled() {
  const rawValue = import.meta.env.VITE_TDS_RECRUITER_DECISION_UI_ENABLED;

  if (typeof rawValue === "boolean") {
    return rawValue;
  }

  if (typeof rawValue !== "string") {
    return false;
  }

  return TRUE_VALUES.has(rawValue.trim().toLowerCase());
}

const DECISION_STATE_LABELS = {
  PROCEED: "Proceed",
  PROCEED_WITH_CONDITIONS: "Proceed with Conditions",
  DO_NOT_PROCEED: "Do Not Proceed",
  INSUFFICIENT_EVIDENCE: "Insufficient Evidence / No Judgement",
};

const INTEGRITY_STATUS_LABELS = {
  CLEAN: "Clean",
  MIXED: "Mixed",
  AT_RISK: "At Risk",
  INVALID: "Invalid",
};

export function getDecisionStateLabel(decision) {
  if (decision?.decision_state_label && typeof decision.decision_state_label === "string") {
    return decision.decision_state_label;
  }

  return DECISION_STATE_LABELS[decision?.decision_state] ?? "Unknown Decision State";
}

export function getIntegrityStatusLabel(integrityStatus) {
  if (typeof integrityStatus !== "string" || integrityStatus.trim() === "") {
    return "Unknown";
  }

  return INTEGRITY_STATUS_LABELS[integrityStatus] ?? integrityStatus
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatDecisionTimestamp(createdAt) {
  if (typeof createdAt !== "string" || createdAt.trim() === "") {
    return null;
  }

  const parsed = new Date(createdAt);
  if (Number.isNaN(parsed.getTime())) {
    return createdAt;
  }

  return parsed.toLocaleString();
}

export async function loadInterviewDecisionOutcome(
  interviewId,
  {
    enabled = isTdsRecruiterDecisionUiEnabled(),
    api = null,
  } = {},
) {
  if (!enabled || !interviewId) {
    return { status: "disabled", decision: null };
  }

  const apiClient = api ?? interviewsApi;

  try {
    const decision = await apiClient.getInterviewDecision(interviewId);
    return { status: "success", decision };
  } catch (error) {
    if (error?.status === 404) {
      return { status: "unavailable", decision: null };
    }

    if (error?.status === 403) {
      return { status: "forbidden", decision: null };
    }

    return { status: "error", decision: null };
  }
}
