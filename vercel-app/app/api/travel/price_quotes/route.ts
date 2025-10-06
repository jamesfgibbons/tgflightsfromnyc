export const runtime = 'edge';

export async function GET(req: Request) {
  const backend = process.env.BACKEND_BASE_URL!;
  const { search } = new URL(req.url);
  const res = await fetch(`${backend}/api/travel/price_quotes${search}`, { headers: { accept: 'application/json' } });
  if (res.ok) {
    const text = await res.text();
    return new Response(text, { status: res.status, headers: { 'content-type': 'application/json' } });
  }
  const sample = {
    total: 5,
    items: [
      { origin: 'JFK', destination: 'LAX', price: 245, brand: 'Delta', airline: 'DL' },
      { origin: 'JFK', destination: 'SFO', price: 265, brand: 'United', airline: 'UA' },
      { origin: 'EWR', destination: 'MIA', price: 159, brand: 'JetBlue', airline: 'B6' },
      { origin: 'LGA', destination: 'ORD', price: 139, brand: 'American', airline: 'AA' },
      { origin: 'EWR', destination: 'SFO', price: 278, brand: 'United', airline: 'UA' }
    ]
  };
  return new Response(JSON.stringify(sample), { status: 200, headers: { 'content-type': 'application/json', 'x-fallback': '1' } });
}
