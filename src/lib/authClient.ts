import { apiClient } from "./apiClient";

export type AuthSession = {
  accessToken: string;
};

export type UserProfile = {
  id: string;
  email: string;
  full_name?: string | null;
  created_at: string;
};

class AuthClient {
  private session: AuthSession | null = null;

  getSession() {
    return this.session;
  }

  async register(email: string, password: string, fullName?: string) {
    return apiClient.post<UserProfile>("/api/auth/register", {
      email,
      password,
      full_name: fullName,
    });
  }

  async login(email: string, password: string) {
    const response = await apiClient.post<{ access_token: string }>("/api/auth/login", {
      email,
      password,
    });
    this.session = { accessToken: response.access_token };
    apiClient.setAccessToken(response.access_token);
    return response;
  }

  async refresh() {
    const response = await apiClient.post<{ access_token: string }>("/api/auth/refresh");
    this.session = { accessToken: response.access_token };
    apiClient.setAccessToken(response.access_token);
    return response;
  }

  async logout() {
    await apiClient.post("/api/auth/logout");
    this.session = null;
    apiClient.setAccessToken(null);
  }

  async me() {
    return apiClient.get<UserProfile>("/api/auth/me");
  }
}

export const authClient = new AuthClient();
