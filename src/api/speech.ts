import { http } from "./http";

export interface SpeechTokenResponse {
  token: string;
  region: string;
}

export const speechApi = {
  getToken() {
    return http.post<SpeechTokenResponse>("/api/v1/speech/token");
  },
};
