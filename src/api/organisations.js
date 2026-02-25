import { http } from "./http";
export const organisationsApi = {
    create(payload) {
        return http.post("/api/orgs", payload);
    },
    getCurrentMembership() {
        return http.get("/api/orgs/current");
    },
    updateRetention(organisationId, retentionDays) {
        return http.patch(`/api/orgs/${organisationId}/retention`, {
            recording_retention_days: retentionDays,
        });
    },
    getStats(organisationId) {
        return http.get(`/api/orgs/${organisationId}/stats`);
    },
};
