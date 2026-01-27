import { http } from "./http";

export const scoringApi = {
  scoreInterview(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/scoring/analyze", payload);
  },
};
