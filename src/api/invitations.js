import { http } from "./http";
export const invitationsApi = {
    send(payload) {
        return http.post("/api/invitations", payload);
    },
    validate(token) {
        return http.get("/api/v1/invitations/validate", { token });
    },
    listByApplication(applicationId) {
        return http.get("/api/v1/invitations", { application_id: applicationId });
    },
    update(invitationId, payload) {
        return http.patch(`/api/v1/invitations/${invitationId}`, payload);
    },
};
