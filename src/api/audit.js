import { http } from "./http";
export const auditApi = {
    list(organisationId) {
        return http.get("/api/v1/audit-log", { organisation_id: organisationId });
    },
    create(payload) {
        return http.post("/api/v1/audit-log", payload);
    },
};
