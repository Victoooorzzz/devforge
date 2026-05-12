// packages/core/lib/auth.ts

const TOKEN_KEY = "devforge_auth_status";

export function setToken(token?: string): void {
  // Token is now set via HttpOnly cookie by backend.
  // devforge_auth_status is also set by backend, so we don't strictly need to do anything here.
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_KEY}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function removeToken(): Promise<void> {
  if (typeof window !== "undefined") {
    document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (e) {
      // Ignore network errors on logout
    }
  }
}

export function isAuthenticated(): boolean {
  return getToken() === "true";
}

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(options.headers);

  // Use cookies for auth
  options.credentials = "include";

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

export async function login(email: string, password: string): Promise<{ success: boolean; error?: string; isEmailVerified?: boolean }> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include'
    });

    const data = await response.json();

    if (response.ok) {
      return { success: true, isEmailVerified: data.is_email_verified };
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
      credentials: 'include'
    });

    const data = await response.json();

    if (response.ok) {
      return { success: true };
    }

    return { success: false, error: data.detail || 'Verification failed' };
  } catch (err) {
    return { success: false, error: 'Connection error' };
  }
}

export async function register(data: { email: string; password: string; app_name?: string; [key: string]: any }): Promise<{ success: boolean; error?: string; isEmailVerified?: boolean; checkoutUrl?: string }> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      credentials: 'include'
    });

    const result = await response.json();

    if (response.ok) {
      return { 
        success: true, 
        isEmailVerified: result.is_email_verified,
        checkoutUrl: result.checkout_url 
      };
    }

    return { success: false, error: result.detail || 'Registration failed' };
  } catch (err) {
    return { success: false, error: 'Connection error' };
  }
}
