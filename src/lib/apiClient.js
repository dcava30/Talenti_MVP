const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
class ApiClient {
    constructor() {
        this.accessToken = null;
    }
    setAccessToken(token) {
        this.accessToken = token;
    }
    async request(path, options = {}) {
        const headers = new Headers(options.headers);
        headers.set("Content-Type", "application/json");
        if (this.accessToken) {
            headers.set("Authorization", `Bearer ${this.accessToken}`);
        }
        const response = await fetch(`${API_BASE_URL}${path}`, {
            ...options,
            headers,
            credentials: "include",
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Request failed (${response.status})`);
        }
        return response.json();
    }
    get(path) {
        return this.request(path);
    }
    post(path, body) {
        return this.request(path, {
            method: "POST",
            body: body ? JSON.stringify(body) : undefined,
        });
    }
}
export const apiClient = new ApiClient();
