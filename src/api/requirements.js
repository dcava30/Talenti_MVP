import { http } from "./http";
export const requirementsApi = {
    extract(payload) {
        return http.post("/api/v1/roles/extract-requirements", payload);
    },
};
