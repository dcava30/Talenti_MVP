import { authTokenStorage, http } from "./http";
export const authApi = {
    getToken() {
        return authTokenStorage.get();
    },
    setToken(token) {
        authTokenStorage.set(token);
    },
    clearToken() {
        authTokenStorage.clear();
    },
    async register(payload) {
        return http.post("/api/auth/register", payload);
    },
    async login(payload) {
        const response = await http.post("/api/auth/login", payload);
        authTokenStorage.set(response.access_token);
        return response;
    },
    async logout() {
        await http.post("/api/auth/logout");
        authTokenStorage.clear();
    },
    async me() {
        return http.get("/api/auth/me");
    },
};
