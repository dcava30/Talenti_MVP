import { http } from "./http";

export const resumeApi = {
  parse(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/parse-resume", payload);
  },
};
