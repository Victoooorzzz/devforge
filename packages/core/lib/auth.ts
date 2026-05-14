// packages/core/lib/auth.ts

const JWT_KEY = "devforge_token";

export function setToken(token?: string): void {
  if (typeof window === "undefined" || !token) return;
  localStorage.setItem(JWT_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(JWT_KEY);
}

export function isTokenSaved(): boolean {
  return !!getToken();
}

export async function removeToken(): Promise<void> {
  if (typeof window !== "undefined") {
    localStorage.removeItem(JWT_KEY);
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
  return !!getToken();
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
      if (data.access_token) setToken(data.access_token);

      // If account not verified, auto-send a fresh code before redirecting to /verify
      if (data.is_email_verified === false) {
        try {
          await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/resend-code`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(data.access_token ? { 'Authorization': `Bearer ${data.access_token}` } : {}),
            },
            credentials: 'include',
          });
        } catch {
          // Non-blocking — user can still click resend manually on /verify
        }
      }

      return { success: true, isEmailVerified: data.is_email_verified };
    }

    return { success: false, error: data.detail || 'Login failed' };
  } catch (err) {
    return { success: false, error: 'Connection error' };
  }
}

export async function verify(code: string): Promise<{ success: boolean; error?: string }> {
  try {
    const token = getToken();
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ code }),
      credentials: 'include',
    });

    const data = await response.json();

    if (response.ok) {
      // Refresh token from response if backend sends a new one
      if (data.access_token) setToken(data.access_token);
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
      // Save JWT to localStorage so /auth/verify can send it as Authorization: Bearer
      if (result.access_token) setToken(result.access_token);
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
