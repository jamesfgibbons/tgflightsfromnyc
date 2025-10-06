export const runtime = 'edge';

export async function GET(req: Request) {
  const backend = process.env.BACKEND_BASE_URL!;
  const { search } = new URL(req.url);
  const res = await fetch(`${backend}/api/travel/price_quotes_latest${search}`, { headers: { accept: 'application/json' } });
  if (res.ok) {
    const text = await res.text();
    return new Response(text, { status: res.status, headers: { 'content-type': 'application/json' } });
  }
  // Fallback sample for previews
  const sample = { total: 3, items: [
    { origin: 'JFK', destination: 'LAX', window_days: 45, price_low_usd: 240, price_high_usd: 310, typical_airlines: ['DL','AA'], cited_websites: ['skyscanner.com'], brands: ['Delta','American'], created_at: new Date().toISOString() },
    { origin: 'EWR', destination: 'MIA', window_days: 45, price_low_usd: 159, price_high_usd: 220, typical_airlines: ['B6','UA'], cited_websites: ['jetblue.com'], brands: ['JetBlue'], created_at: new Date().toISOString() },
    { origin: 'LGA', destination: 'ORD', window_days: 45, price_low_usd: 139, price_high_usd: 200, typical_airlines: ['AA'], cited_websites: ['aa.com'], brands: ['American'], created_at: new Date().toISOString() },
  ]};
  return new Response(JSON.stringify(sample), { status: 200, headers: { 'content-type': 'application/json', 'x-fallback': '1' } });
}

