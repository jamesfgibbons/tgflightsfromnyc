import { NextRequest, NextResponse } from 'next/server';

export function middleware(req: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASS;
  if (!user || !pass) return NextResponse.next();

  const auth = req.headers.get('authorization');
  if (!auth?.startsWith('Basic ')) {
    return new Response('Authentication required.', {
      status: 401,
      headers: { 'WWW-Authenticate': 'Basic realm="VibeNet"' },
    });
  }
  try {
    const [, b64] = auth.split(' ');
    const [u, p] = atob(b64).split(':');
    if (u === user && p === pass) return NextResponse.next();
  } catch {}
  return new Response('Unauthorized', { status: 401, headers: { 'WWW-Authenticate': 'Basic realm="VibeNet"' } });
}

export const config = {
  matcher: ['/((?!api/cron).*)'],
};

