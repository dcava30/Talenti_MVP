import { http } from "./http";

export const requirementsApi = {
  extract(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/roles/extract-requirements", payload);
  },
};
