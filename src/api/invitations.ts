import { http } from "./http";

export const invitationsApi = {
  send(payload: Record<string, unknown>) {
    return http.post<any>("/api/invitations", payload);
  },
  validate(token: string) {
    return http.get<any>("/api/v1/invitations/validate", { token });
  },
  listByApplication(applicationId: string) {
    return http.get<any[]>("/api/v1/invitations", { application_id: applicationId });
  },
  update(invitationId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/invitations/${invitationId}`, payload);
  },
};
