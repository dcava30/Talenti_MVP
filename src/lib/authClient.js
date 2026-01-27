import { apiClient } from "./apiClient";
class AuthClient {
    constructor() {
        this.session = null;
    }
    getSession() {
        return this.session;
    }
    async register(email, password, fullName) {
        return apiClient.post("/api/auth/register", {
            email,
            password,
            full_name: fullName,
        });
    }
    async login(email, password) {
        const response = await apiClient.post("/api/auth/login", {
            email,
            password,
        });
        this.session = { accessToken: response.access_token };
        apiClient.setAccessToken(response.access_token);
        return response;
    }
    async refresh() {
        const response = await apiClient.post("/api/auth/refresh");
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
        return apiClient.get("/api/auth/me");
    }
}
export const authClient = new AuthClient();
