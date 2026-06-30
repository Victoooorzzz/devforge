import crypto from 'crypto';
import { cookies } from 'next/headers';

export interface UserSession {
  userId: number;
  email: string;
  exp: number;
}

export function verifyJwt(token: string, secret: string): UserSession | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const [headerB64, payloadB64, signatureB64] = parts;

    const signInput = `${headerB64}.${payloadB64}`;
    const expectedSignature = crypto
      .createHmac('sha256', secret)
      .update(signInput)
      .digest('base64url');

    // Constant time comparison to prevent timing attacks
    const a = Buffer.from(signatureB64);
    const b = Buffer.from(expectedSignature);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
      return null;
    }

    const payloadJson = Buffer.from(payloadB64, 'base64url').toString('utf8');
    const payload = JSON.parse(payloadJson);

    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) {
      return null;
    }

    return {
      userId: parseInt(payload.sub),
      email: payload.email,
      exp: payload.exp
    };
  } catch (e) {
    return null;
  }
}

export function getServerUser(): UserSession | null {
  try {
    const cookieStore = cookies();
    const token = cookieStore.get('devforge_token')?.value;
    if (!token) return null;

    const secret = process.env.JWT_SECRET || 'change-me-in-production';
    return verifyJwt(token, secret);
  } catch (e) {
    return null;
  }
}
