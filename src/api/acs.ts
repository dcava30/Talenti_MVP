import { http } from "./http";

export interface AcsTokenResponse {
  token: string;
  expires_on: string;
  user_id: string;
}

export const acsApi = {
  getToken(scopes: string[]) {
    return http.post<AcsTokenResponse>("/api/v1/acs/token", { scopes });
  },
};
