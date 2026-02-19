import { http } from "./http";
export const shortlistApi = {
    generate(payload) {
        return http.post("/api/v1/shortlist/generate", payload);
    },
};
