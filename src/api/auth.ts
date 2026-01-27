import { authTokenStorage, http } from "./http";

export interface AuthTokenResponse {
  access_token: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name?: string | null;
  created_at?: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authApi = {
  getToken() {
    return authTokenStorage.get();
  },
  setToken(token: string) {
    authTokenStorage.set(token);
  },
  clearToken() {
    authTokenStorage.clear();
  },
  async register(payload: RegisterPayload) {
    return http.post<AuthUser>("/api/auth/register", payload);
  },
  async login(payload: LoginPayload) {
    const response = await http.post<AuthTokenResponse>("/api/auth/login", payload);
    authTokenStorage.set(response.access_token);
    return response;
  },
  async logout() {
    await http.post("/api/auth/logout");
    authTokenStorage.clear();
  },
  async me() {
    return http.get<AuthUser>("/api/auth/me");
  },
};
