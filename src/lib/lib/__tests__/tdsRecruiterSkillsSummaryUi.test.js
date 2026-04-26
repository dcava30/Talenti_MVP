import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("tds recruiter skills summary ui helpers", () => {
  it("defaults the recruiter skills summary ui flag off", async () => {
    vi.stubEnv("VITE_TDS_RECRUITER_SKILLS_SUMMARY_UI_ENABLED", "");
    const { isTdsRecruiterSkillsSummaryUiEnabled } = await import("../tdsRecruiterSkillsSummaryUi");

    expect(isTdsRecruiterSkillsSummaryUiEnabled()).toBe(false);
  });

  it("does not call the skills summary api when the ui flag is off", async () => {
    const getInterviewSkillsAssessmentSummary = vi.fn();
    const { loadInterviewSkillsAssessmentSummary } = await import("../tdsRecruiterSkillsSummaryUi");

    const result = await loadInterviewSkillsAssessmentSummary("int-1", {
      enabled: false,
      api: { getInterviewSkillsAssessmentSummary },
    });

    expect(result).toEqual({ status: "disabled", summary: null });
    expect(getInterviewSkillsAssessmentSummary).not.toHaveBeenCalled();
  });

  it("calls the skills summary api when the ui flag is on", async () => {
    const summary = { skills_summary_id: "sum-1" };
    const getInterviewSkillsAssessmentSummary = vi.fn().mockResolvedValue(summary);
    const { loadInterviewSkillsAssessmentSummary } = await import("../tdsRecruiterSkillsSummaryUi");

    const result = await loadInterviewSkillsAssessmentSummary("int-1", {
      enabled: true,
      api: { getInterviewSkillsAssessmentSummary },
    });

    expect(getInterviewSkillsAssessmentSummary).toHaveBeenCalledWith("int-1");
    expect(result).toEqual({ status: "success", summary });
  });

  it("maps 404 responses to the unavailable state", async () => {
    const getInterviewSkillsAssessmentSummary = vi.fn().mockRejectedValue({ status: 404 });
    const { loadInterviewSkillsAssessmentSummary } = await import("../tdsRecruiterSkillsSummaryUi");

    const result = await loadInterviewSkillsAssessmentSummary("int-1", {
      enabled: true,
      api: { getInterviewSkillsAssessmentSummary },
    });

    expect(result).toEqual({ status: "unavailable", summary: null });
  });

  it("maps 403 responses to the access denied state", async () => {
    const getInterviewSkillsAssessmentSummary = vi.fn().mockRejectedValue({ status: 403 });
    const { loadInterviewSkillsAssessmentSummary } = await import("../tdsRecruiterSkillsSummaryUi");

    const result = await loadInterviewSkillsAssessmentSummary("int-1", {
      enabled: true,
      api: { getInterviewSkillsAssessmentSummary },
    });

    expect(result).toEqual({ status: "forbidden", summary: null });
  });

  it("maps unexpected failures to the generic error state", async () => {
    const getInterviewSkillsAssessmentSummary = vi.fn().mockRejectedValue(new Error("boom"));
    const { loadInterviewSkillsAssessmentSummary } = await import("../tdsRecruiterSkillsSummaryUi");

    const result = await loadInterviewSkillsAssessmentSummary("int-1", {
      enabled: true,
      api: { getInterviewSkillsAssessmentSummary },
    });

    expect(result).toEqual({ status: "error", summary: null });
  });
});
