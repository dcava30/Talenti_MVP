import { http } from "./http";
export const resumeApi = {
    parse(payload) {
        return http.post("/api/v1/candidates/parse-resume", payload);
    },
};
