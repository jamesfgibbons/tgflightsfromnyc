export const runtime = 'edge';

export async function GET() {
  const backend = process.env.BACKEND_BASE_URL!;
  const res = await fetch(`${backend}/api/llm/run`, {
    method: 'POST',
    headers: { 'x-admin-secret': process.env.ADMIN_SECRET ?? '' },
  });
  const text = await res.text();
  return new Response(text, { status: res.status, headers: { 'content-type': 'application/json' } });
}

