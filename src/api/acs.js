import { http } from "./http";
export const acsApi = {
    getToken(scopes) {
        return http.post("/api/v1/acs/token", { scopes });
    },
};
