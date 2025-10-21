/**
 * Deal Awareness API Client
 *
 * Provides functions to evaluate deal quality and get booking recommendations.
 * Connects to /api/deals/* endpoints.
 */

// Get API base from config or environment
export const API_BASE =
  (window as any).__APP_CONFIG__?.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE ||
  'http://localhost:8000';

/**
 * Baseline price distribution (30-day rolling)
 */
export interface Baseline {
  p25: number;        // 25th percentile
  p50: number;        // 50th percentile (median)
  p75: number;        // 75th percentile
  samples: number;    // Number of price observations
  last_updated?: string;
}

/**
 * Optimal booking window (sweet-spot)
 */
export interface SweetSpot {
  min_days: number;   // Minimum lead time
  max_days: number;   // Maximum lead time
}

/**
 * Deal evaluation response
 */
export interface DealEvaluation {
  has_data: boolean;
  message?: string;
  origin: string;
  dest: string;
  month: number;               // 1-12
  cabin: string;
  depart_month?: string;       // YYYY-MM-DD
  current_price?: number;
  baseline?: Baseline;
  delta_pct?: number;          // % vs median baseline
  deal_score?: number;         // 0-100
  sweet_spot?: SweetSpot | null;
  recommendation?: 'BUY' | 'TRACK' | 'WAIT';
  confidence?: number;         // 0-100
  rationale?: string;
  last_seen?: string;
}

/**
 * Evaluate deal quality for a route and month
 *
 * @param origin - Origin airport code (e.g., "JFK")
 * @param dest - Destination airport code (e.g., "MIA")
 * @param month - Departure month (1-12)
 * @param cabin - Cabin class (default: "economy")
 * @returns Deal evaluation with BUY/TRACK/WAIT recommendation
 */
export async function evaluateDeal(
  origin: string,
  dest: string,
  month: number,
  cabin: string = 'economy'
): Promise<DealEvaluation> {
  const url = new URL(`${API_BASE}/api/deals/evaluate`);
  url.searchParams.set('origin', origin.toUpperCase());
  url.searchParams.set('dest', dest.toUpperCase());
  url.searchParams.set('month', String(month));
  url.searchParams.set('cabin', cabin.toLowerCase());

  const response = await fetch(url.toString());

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(error.message || `Deal evaluation failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Batch evaluate multiple routes
 *
 * @param routes - Array of {origin, dest, month, cabin?} objects
 * @returns Array of deal evaluations
 */
export async function batchEvaluateDeal(
  routes: Array<{
    origin: string;
    dest: string;
    month: number;
    cabin?: string;
  }>
): Promise<DealEvaluation[]> {
  const response = await fetch(`${API_BASE}/api/deals/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ routes })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(error.message || `Batch evaluation failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get recommendation color based on type
 */
export function getRecommendationColor(recommendation?: string): string {
  switch (recommendation) {
    case 'BUY':
      return 'text-glow-lime';
    case 'WAIT':
      return 'text-glow-magenta';
    case 'TRACK':
      return 'text-note-cyan';
    default:
      return 'text-text-dim';
  }
}

/**
 * Get recommendation badge variant
 */
export function getRecommendationBadge(recommendation?: string): string {
  switch (recommendation) {
    case 'BUY':
      return 'bg-glow-lime/20 text-glow-lime border-glow-lime';
    case 'WAIT':
      return 'bg-glow-magenta/20 text-glow-magenta border-glow-magenta';
    case 'TRACK':
      return 'bg-note-cyan/20 text-note-cyan border-note-cyan';
    default:
      return 'bg-ink-700 text-text-dim border-ink-500';
  }
}

/**
 * Format delta percentage with sign and color
 */
export function formatDelta(delta_pct?: number): {
  text: string;
  color: string;
} {
  if (delta_pct === undefined || delta_pct === null) {
    return { text: 'N/A', color: 'text-text-dim' };
  }

  const sign = delta_pct > 0 ? '+' : '';
  const color = delta_pct <= 0 ? 'text-glow-lime' : 'text-glow-magenta';

  return {
    text: `${sign}${delta_pct.toFixed(1)}%`,
    color
  };
}

/**
 * Get deal score color based on value
 */
export function getDealScoreColor(score?: number): string {
  if (!score) return 'text-text-dim';
  if (score >= 80) return 'text-glow-lime';
  if (score >= 60) return 'text-note-cyan';
  if (score >= 40) return 'text-glow-yellow';
  return 'text-glow-magenta';
}
