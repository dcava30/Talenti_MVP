import { http } from "./http";
export const speechApi = {
    getToken() {
        return http.post("/api/v1/speech/token");
    },
};
