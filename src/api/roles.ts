import { http } from "./http";

export interface RoleCreatePayload {
  organisation_id: string;
  title: string;
  description?: string | null;
  department?: string | null;
  location?: string | null;
  work_type?: string | null;
  employment_type?: string | null;
  salary_range_min?: number | null;
  salary_range_max?: number | null;
  requirements?: unknown;
  scoring_rubric?: unknown;
  interview_structure?: unknown;
  status?: string;
  created_by?: string | null;
}

export interface RoleResponse {
  id: string;
  organisation_id: string;
  title: string;
  status?: string;
  description?: string | null;
  requirements?: unknown;
  scoring_rubric?: unknown;
  interview_structure?: unknown;
  created_at?: string;
  updated_at?: string;
}

export const rolesApi = {
  create(payload: RoleCreatePayload) {
    return http.post<RoleResponse>("/api/roles", payload);
  },
  listAll(params?: { limit?: number }) {
    return http.get<RoleResponse[]>("/api/v1/roles", params);
  },
  listByOrganisation(organisationId: string) {
    return http.get<RoleResponse[]>("/api/roles", { organisation_id: organisationId });
  },
  getById(roleId: string) {
    return http.get<RoleResponse>(`/api/roles/${roleId}`);
  },
  update(roleId: string, payload: Partial<RoleCreatePayload>) {
    return http.patch<RoleResponse>(`/api/roles/${roleId}`, payload);
  },
  updateRubric(roleId: string, payload: { scoring_rubric: unknown }) {
    return http.patch<RoleResponse>(`/api/roles/${roleId}/rubric`, payload);
  },
  listApplications(roleId: string) {
    return http.get<any[]>(`/api/v1/roles/${roleId}/applications`);
  },
};
