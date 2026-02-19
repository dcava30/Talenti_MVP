const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "talenti_auth_token";
export class ApiError extends Error {
    constructor(message, status, details) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.details = details;
    }
}
export const authTokenStorage = {
    get() {
        return localStorage.getItem(TOKEN_STORAGE_KEY);
    },
    set(token) {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
    },
    clear() {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
    },
};
const isJsonResponse = (response) => {
    const contentType = response.headers.get("content-type");
    return contentType?.includes("application/json");
};
const buildQueryString = (params) => {
    if (!params)
        return "";
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null)
            return;
        searchParams.set(key, String(value));
    });
    const query = searchParams.toString();
    return query ? `?${query}` : "";
};
const parseErrorMessage = async (response) => {
    if (isJsonResponse(response)) {
        try {
            const payload = await response.json();
            const message = payload?.detail || payload?.message || response.statusText;
            return { message: typeof message === "string" ? message : response.statusText, details: payload };
        }
        catch {
            return { message: response.statusText };
        }
    }
    const text = await response.text();
    return { message: text || response.statusText };
};
export async function request(path, options = {}) {
    const { params, ...fetchOptions } = options;
    const token = authTokenStorage.get();
    const headers = new Headers(fetchOptions.headers);
    if (!headers.has("Accept")) {
        headers.set("Accept", "application/json");
    }
    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }
    const isFormData = fetchOptions.body instanceof FormData;
    if (!isFormData && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
    const response = await fetch(`${API_BASE_URL}${path}${buildQueryString(params)}`, {
        ...fetchOptions,
        headers,
        credentials: "include",
    });
    if (!response.ok) {
        const { message, details } = await parseErrorMessage(response);
        throw new ApiError(message, response.status, details);
    }
    if (response.status === 204) {
        return null;
    }
    if (isJsonResponse(response)) {
        return response.json();
    }
    return response.text();
}
export const http = {
    get(path, params) {
        return request(path, { method: "GET", params });
    },
    post(path, body) {
        return request(path, {
            method: "POST",
            body: body ? JSON.stringify(body) : undefined,
        });
    },
    put(path, body) {
        return request(path, {
            method: "PUT",
            body: body ? JSON.stringify(body) : undefined,
        });
    },
    patch(path, body) {
        return request(path, {
            method: "PATCH",
            body: body ? JSON.stringify(body) : undefined,
        });
    },
    delete(path, body) {
        return request(path, {
            method: "DELETE",
            body: body ? JSON.stringify(body) : undefined,
        });
    },
};
