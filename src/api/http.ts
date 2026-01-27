const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "talenti_auth_token";

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export const authTokenStorage = {
  get(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  },
  set(token: string) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  },
  clear() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  },
};

const isJsonResponse = (response: Response) => {
  const contentType = response.headers.get("content-type");
  return contentType?.includes("application/json");
};

const buildQueryString = (params?: Record<string, string | number | boolean | undefined | null>) => {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
};

const parseErrorMessage = async (response: Response): Promise<{ message: string; details?: unknown }> => {
  if (isJsonResponse(response)) {
    try {
      const payload = await response.json();
      const message = payload?.detail || payload?.message || response.statusText;
      return { message: typeof message === "string" ? message : response.statusText, details: payload };
    } catch {
      return { message: response.statusText };
    }
  }

  const text = await response.text();
  return { message: text || response.statusText };
};

export async function request<T>(
  path: string,
  options: RequestInit & { params?: Record<string, string | number | boolean | undefined | null> } = {}
): Promise<T> {
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
    return null as T;
  }

  if (isJsonResponse(response)) {
    return response.json() as Promise<T>;
  }

  return response.text() as unknown as T;
}

export const http = {
  get<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>) {
    return request<T>(path, { method: "GET", params });
  },
  post<T>(path: string, body?: unknown) {
    return request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
  put<T>(path: string, body?: unknown) {
    return request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
  patch<T>(path: string, body?: unknown) {
    return request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
  delete<T>(path: string, body?: unknown) {
    return request<T>(path, {
      method: "DELETE",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
};
