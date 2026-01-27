import { http } from "./http";

export const auditApi = {
  list(organisationId: string) {
    return http.get<any[]>("/api/v1/audit-log", { organisation_id: organisationId });
  },
  create(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/audit-log", payload);
  },
};
