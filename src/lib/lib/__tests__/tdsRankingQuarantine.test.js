import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("tds ranking quarantine helpers", () => {
  it("defaults the quarantine flag off", async () => {
    vi.stubEnv("VITE_TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED", "");
    const { isTdsRankingAndShortlistQuarantineEnabled } = await import("../tdsRankingQuarantine");

    expect(isTdsRankingAndShortlistQuarantineEnabled()).toBe(false);
  });

  it("keeps match-score sorting when the quarantine flag is off", async () => {
    vi.stubEnv("VITE_TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED", "false");
    const { sortRoleApplications, shouldShowAiMatchSorting, shouldShowApplicationMatchScore } = await import("../tdsRankingQuarantine");
    const applications = [
      { id: "app-1", match_score: 25 },
      { id: "app-2", match_score: 90 },
      { id: "app-3", match_score: null },
    ];

    expect(sortRoleApplications(applications).map((application) => application.id)).toEqual(["app-2", "app-1", "app-3"]);
    expect(shouldShowAiMatchSorting(applications)).toBe(true);
    expect(shouldShowApplicationMatchScore(applications[0])).toBe(true);
  });

  it("turns off shortlist ranking affordances when the quarantine flag is on", async () => {
    vi.stubEnv("VITE_TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED", "true");
    const { sortRoleApplications, shouldShowAiMatchSorting, shouldShowApplicationMatchScore } = await import("../tdsRankingQuarantine");
    const applications = [
      { id: "app-1", match_score: 25 },
      { id: "app-2", match_score: 90 },
    ];

    expect(sortRoleApplications(applications).map((application) => application.id)).toEqual(["app-1", "app-2"]);
    expect(shouldShowAiMatchSorting(applications)).toBe(false);
    expect(shouldShowApplicationMatchScore(applications[0])).toBe(false);
  });
});
