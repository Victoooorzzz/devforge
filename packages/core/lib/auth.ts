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

export async function login(email: string, password: string): Promise<{ success: boolean; token?: string; error?: string; isEmailVerified?: boolean }> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (response.ok) {
      setToken(data.access_token);
      return { success: true, token: data.access_token, isEmailVerified: data.is_email_verified };
    }

    return { success: false, error: data.detail || 'Login failed' };
  } catch (err) {
    return { success: false, error: 'Connection error' };
  }
}

export async function verify(code: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetchWithAuth(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });

    const data = await response.json();

    if (response.ok) {
      if (data.access_token) {
        setToken(data.access_token);
      }
      return { success: true };
    }

    return { success: false, error: data.detail || 'Verification failed' };
  } catch (err) {
    return { success: false, error: 'Connection error' };
  }
}

export async function register(data: { email: string; password: string; [key: string]: any }): Promise<{ success: boolean; error?: string; isEmailVerified?: boolean }> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (response.ok) {
      if (result.access_token) {
        setToken(result.access_token);
      }
      return { success: true, isEmailVerified: result.is_email_verified };
    }

    return { success: false, error: result.detail || 'Registration failed' };
  } catch (err) {
    return { success: false, error: 'Connection error' };
  }
}
