import { interviewsApi } from "@/api/interviews";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

export function isTdsRecruiterSkillsSummaryUiEnabled() {
  const rawValue = import.meta.env.VITE_TDS_RECRUITER_SKILLS_SUMMARY_UI_ENABLED;

  if (typeof rawValue === "boolean") {
    return rawValue;
  }

  if (typeof rawValue !== "string") {
    return false;
  }

  return TRUE_VALUES.has(rawValue.trim().toLowerCase());
}

export function formatSkillsSummaryTimestamp(createdAt) {
  if (typeof createdAt !== "string" || createdAt.trim() === "") {
    return null;
  }

  const parsed = new Date(createdAt);
  if (Number.isNaN(parsed.getTime())) {
    return createdAt;
  }

  return parsed.toLocaleString();
}

export async function loadInterviewSkillsAssessmentSummary(
  interviewId,
  {
    enabled = isTdsRecruiterSkillsSummaryUiEnabled(),
    api = null,
  } = {},
) {
  if (!enabled || !interviewId) {
    return { status: "disabled", summary: null };
  }

  const apiClient = api ?? interviewsApi;

  try {
    const summary = await apiClient.getInterviewSkillsAssessmentSummary(interviewId);
    return { status: "success", summary };
  } catch (error) {
    if (error?.status === 404) {
      return { status: "unavailable", summary: null };
    }

    if (error?.status === 403) {
      return { status: "forbidden", summary: null };
    }

    return { status: "error", summary: null };
  }
}
