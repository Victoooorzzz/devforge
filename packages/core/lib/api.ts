// packages/core/lib/api.ts

import { getToken, removeToken } from "./auth";

const DEFAULT_API_BASE = "http://localhost:8000";

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

export function getApiBaseUrl(): string {
  return (API_BASE || DEFAULT_API_BASE).replace(/\/+$/, "");
}

export function getApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

function authHeaders(extraHeaders?: HeadersInit): Record<string, string> {
  const token = getToken();
  return {
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...(extraHeaders as Record<string, string> | undefined),
  };
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeaders(options.headers),
  };

  options.credentials = "include";

  const response = await fetch(getApiUrl(path), {
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

  patch: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>("PATCH", path, body, options),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>("DELETE", path, undefined, options),
};

export function uploadFile<T = unknown>(
  path: string,
  formData: FormData
): Promise<ApiResponse<T>> {
  return fetch(getApiUrl(path), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
    credentials: "include",
  }).then(async (response) => {
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw { detail: errorBody.detail, status: response.status } as ApiError;
    }
    const data = await response.json();
    return { data, status: response.status };
  });
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(getApiUrl(path), {
    headers: authHeaders(),
    credentials: "include",
  });

  if (response.status === 401) {
    await removeToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw { detail: "Unauthorized", status: 401 } as ApiError;
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: "Download failed" }));
    throw {
      detail: errorBody.detail || "Download failed",
      status: response.status,
    } as ApiError;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].replace(/"/g, ""));
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1] || fallback;
}

export async function uploadAndDownloadFile(
  path: string,
  formData: FormData,
  fallbackFilename: string
): Promise<{ filename: string; metadata?: unknown }> {
  const response = await fetch(getApiUrl(path), {
    method: "POST",
    headers: authHeaders(),
    body: formData,
    credentials: "include",
  });

  if (response.status === 401) {
    await removeToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw { detail: "Unauthorized", status: 401 } as ApiError;
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: "File processing failed" }));
    throw {
      detail: errorBody.detail || "File processing failed",
      status: response.status,
    } as ApiError;
  }

  const filename = filenameFromDisposition(response.headers.get("Content-Disposition"), fallbackFilename);
  const metadataHeader = response.headers.get("X-DevForge-Deep-Clean-Report");
  let metadata: unknown;
  if (metadataHeader) {
    try {
      metadata = JSON.parse(metadataHeader);
    } catch {
      metadata = undefined;
    }
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
  return { filename, metadata };
}
