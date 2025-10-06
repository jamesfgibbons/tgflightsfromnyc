export const runtime = 'edge';

export async function GET(req: Request) {
  const backend = process.env.BACKEND_BASE_URL!;
  const { search } = new URL(req.url);
  const res = await fetch(`${backend}/api/travel/routes_nyc${search}`, { headers: { accept: 'application/json' } });
  if (res.ok) {
    const text = await res.text();
    return new Response(text, { status: res.status, headers: { 'content-type': 'application/json' } });
  }
  // Fallback sample for internal previews without Supabase
  const sample = {
    total: 12,
    items: [
      { origin: 'JFK', destination: 'LAX', destination_name: 'Los Angeles', popularity_score: 0.99 },
      { origin: 'JFK', destination: 'SFO', destination_name: 'San Francisco', popularity_score: 0.97 },
      { origin: 'JFK', destination: 'MIA', destination_name: 'Miami', popularity_score: 0.95 },
      { origin: 'LGA', destination: 'ORD', destination_name: 'Chicago O’Hare', popularity_score: 0.93 },
      { origin: 'LGA', destination: 'ATL', destination_name: 'Atlanta', popularity_score: 0.92 },
      { origin: 'LGA', destination: 'DFW', destination_name: 'Dallas–Fort Worth', popularity_score: 0.90 },
      { origin: 'EWR', destination: 'MCO', destination_name: 'Orlando', popularity_score: 0.94 },
      { origin: 'EWR', destination: 'MIA', destination_name: 'Miami', popularity_score: 0.92 },
      { origin: 'EWR', destination: 'SFO', destination_name: 'San Francisco', popularity_score: 0.91 },
      { origin: 'JFK', destination: 'SEA', destination_name: 'Seattle', popularity_score: 0.89 },
      { origin: 'LGA', destination: 'MIA', destination_name: 'Miami', popularity_score: 0.88 },
      { origin: 'EWR', destination: 'LAX', destination_name: 'Los Angeles', popularity_score: 0.87 }
    ]
  };
  return new Response(JSON.stringify(sample), { status: 200, headers: { 'content-type': 'application/json', 'x-fallback': '1' } });
}
