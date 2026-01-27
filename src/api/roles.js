import { http } from "./http";
export const rolesApi = {
    create(payload) {
        return http.post("/api/roles", payload);
    },
    listAll(params) {
        return http.get("/api/v1/roles", params);
    },
    listByOrganisation(organisationId) {
        return http.get("/api/roles", { organisation_id: organisationId });
    },
    getById(roleId) {
        return http.get(`/api/roles/${roleId}`);
    },
    update(roleId, payload) {
        return http.patch(`/api/roles/${roleId}`, payload);
    },
    updateRubric(roleId, payload) {
        return http.patch(`/api/roles/${roleId}/rubric`, payload);
    },
    listApplications(roleId) {
        return http.get(`/api/v1/roles/${roleId}/applications`);
    },
};
