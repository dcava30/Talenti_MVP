const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

export function isTdsRankingAndShortlistQuarantineEnabled() {
  const rawValue = import.meta.env.VITE_TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED;

  if (typeof rawValue === "boolean") {
    return rawValue;
  }

  if (typeof rawValue !== "string") {
    return false;
  }

  return TRUE_VALUES.has(rawValue.trim().toLowerCase());
}

export function sortRoleApplications(applications, quarantineEnabled = isTdsRankingAndShortlistQuarantineEnabled()) {
  if (!Array.isArray(applications)) {
    return [];
  }

  const items = applications.slice();
  if (quarantineEnabled) {
    return items;
  }

  return items.sort((a, b) => {
    const scoreA = a.match_score ?? 0;
    const scoreB = b.match_score ?? 0;
    return scoreB - scoreA;
  });
}

export function shouldShowAiMatchSorting(applications, quarantineEnabled = isTdsRankingAndShortlistQuarantineEnabled()) {
  if (quarantineEnabled || !Array.isArray(applications)) {
    return false;
  }

  return applications.some((application) => application.match_score !== null && application.match_score !== undefined);
}

export function shouldShowApplicationMatchScore(application, quarantineEnabled = isTdsRankingAndShortlistQuarantineEnabled()) {
  if (quarantineEnabled || !application) {
    return false;
  }

  return application.match_score !== null && application.match_score !== undefined;
}
