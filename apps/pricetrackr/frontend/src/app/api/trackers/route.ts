import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

function authHeader(request: NextRequest): string | null {
  const header = request.headers.get("authorization");
  if (header) return header;

  const token = request.cookies.get("devforge_token")?.value;
  return token ? `Bearer ${token}` : null;
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  const authorization = authHeader(request);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authorization) {
    headers.Authorization = authorization;
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${API_BASE}/trackers`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Price tracker service is unavailable. Try again in a moment." },
      { status: 502 }
    );
  }

  const responseBody = await backendResponse.text();

  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      "Content-Type": backendResponse.headers.get("content-type") || "application/json",
      "Cache-Control": "no-store",
    },
  });
}
