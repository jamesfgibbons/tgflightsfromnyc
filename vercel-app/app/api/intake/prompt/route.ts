export const runtime = 'edge';

export async function POST(req: Request) {
  const backend = process.env.BACKEND_BASE_URL!;
  const payload = await req.text();
  const res = await fetch(`${backend}/api/intake/prompt`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-client-token': process.env.INTAKE_TOKEN ?? ''
    },
    body: payload,
  });
  const text = await res.text();
  return new Response(text, { status: res.status, headers: { 'content-type': 'application/json' } });
}

