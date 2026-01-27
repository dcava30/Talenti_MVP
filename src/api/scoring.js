import { http } from "./http";
export const scoringApi = {
    scoreInterview(payload) {
        return http.post("/api/v1/scoring/analyze", payload);
    },
};
