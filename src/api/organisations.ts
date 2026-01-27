import { http } from "./http";

export interface OrganisationCreatePayload {
  name: string;
  description?: string | null;
  industry?: string | null;
  website?: string | null;
}

export interface OrganisationResponse {
  id: string;
  name: string;
  description?: string | null;
  industry?: string | null;
  website?: string | null;
  created_at?: string;
}

export interface OrgMembershipResponse {
  role: string;
  organisation: OrganisationResponse & {
    values_framework?: unknown;
    recording_retention_days?: number | null;
  };
}

export interface OrgStatsResponse {
  activeRoles: number;
  totalCandidates: number;
  completedInterviews: number;
  avgMatchScore: number;
}

export const organisationsApi = {
  create(payload: OrganisationCreatePayload) {
    return http.post<OrganisationResponse>("/api/orgs", payload);
  },
  getCurrentMembership() {
    return http.get<OrgMembershipResponse>("/api/v1/orgs/current");
  },
  updateRetention(organisationId: string, retentionDays: number) {
    return http.patch<OrganisationResponse>(`/api/v1/orgs/${organisationId}/retention`, {
      recording_retention_days: retentionDays,
    });
  },
  getStats(organisationId: string) {
    return http.get<OrgStatsResponse>(`/api/v1/orgs/${organisationId}/stats`);
  },
};
