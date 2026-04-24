// packages/core/lib/auth.ts

const TOKEN_KEY = "devforge_token";

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax; Secure`;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_KEY}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function removeToken(): void {
  if (typeof window !== "undefined") {
    document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    removeToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return response;
}
