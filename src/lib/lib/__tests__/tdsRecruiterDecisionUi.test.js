import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("tds recruiter decision ui helpers", () => {
  it("defaults the recruiter decision ui flag off", async () => {
    vi.stubEnv("VITE_TDS_RECRUITER_DECISION_UI_ENABLED", "");
    const { isTdsRecruiterDecisionUiEnabled } = await import("../tdsRecruiterDecisionUi");

    expect(isTdsRecruiterDecisionUiEnabled()).toBe(false);
  });

  it("does not call the decision api when the ui flag is off", async () => {
    const getInterviewDecision = vi.fn();
    const { loadInterviewDecisionOutcome } = await import("../tdsRecruiterDecisionUi");

    const result = await loadInterviewDecisionOutcome("int-1", {
      enabled: false,
      api: { getInterviewDecision },
    });

    expect(result).toEqual({ status: "disabled", decision: null });
    expect(getInterviewDecision).not.toHaveBeenCalled();
  });

  it("calls the decision api when the ui flag is on", async () => {
    const decision = { decision_state: "PROCEED" };
    const getInterviewDecision = vi.fn().mockResolvedValue(decision);
    const { loadInterviewDecisionOutcome } = await import("../tdsRecruiterDecisionUi");

    const result = await loadInterviewDecisionOutcome("int-1", {
      enabled: true,
      api: { getInterviewDecision },
    });

    expect(getInterviewDecision).toHaveBeenCalledWith("int-1");
    expect(result).toEqual({ status: "success", decision });
  });

  it("maps 404 responses to the unavailable state", async () => {
    const getInterviewDecision = vi.fn().mockRejectedValue({ status: 404 });
    const { loadInterviewDecisionOutcome } = await import("../tdsRecruiterDecisionUi");

    const result = await loadInterviewDecisionOutcome("int-1", {
      enabled: true,
      api: { getInterviewDecision },
    });

    expect(result).toEqual({ status: "unavailable", decision: null });
  });

  it("maps 403 responses to the access denied state", async () => {
    const getInterviewDecision = vi.fn().mockRejectedValue({ status: 403 });
    const { loadInterviewDecisionOutcome } = await import("../tdsRecruiterDecisionUi");

    const result = await loadInterviewDecisionOutcome("int-1", {
      enabled: true,
      api: { getInterviewDecision },
    });

    expect(result).toEqual({ status: "forbidden", decision: null });
  });

  it("maps unexpected failures to the generic error state", async () => {
    const getInterviewDecision = vi.fn().mockRejectedValue(new Error("boom"));
    const { loadInterviewDecisionOutcome } = await import("../tdsRecruiterDecisionUi");

    const result = await loadInterviewDecisionOutcome("int-1", {
      enabled: true,
      api: { getInterviewDecision },
    });

    expect(result).toEqual({ status: "error", decision: null });
  });
});
