// packages/core/lib/api.ts

import { getToken, removeToken } from "./auth";

const API_BASE = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");

interface ApiResponse<T> {
  data: T;
  status: number;
}

interface ApiError {
  detail: string;
  status: number;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  });

  if (response.status === 401) {
    removeToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw { detail: "Unauthorized", status: 401 } as ApiError;
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: "Request failed" }));
    throw {
      detail: errorBody.detail || "Request failed",
      status: response.status,
    } as ApiError;
  }

  const data = await response.json();
  return { data, status: response.status };
}

export const apiClient = {
  get: <T>(path: string, options?: RequestInit) =>
    request<T>("GET", path, undefined, options),

  post: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>("POST", path, body, options),

  put: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>("PUT", path, body, options),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>("DELETE", path, undefined, options),
};

export function uploadFile(
  path: string,
  formData: FormData
): Promise<ApiResponse<unknown>> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  }).then(async (response) => {
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw { detail: errorBody.detail, status: response.status } as ApiError;
    }
    const data = await response.json();
    return { data, status: response.status };
  });
}
