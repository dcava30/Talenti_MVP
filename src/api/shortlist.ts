import { http } from "./http";

export const shortlistApi = {
  generate(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/shortlist/generate", payload);
  },
};
