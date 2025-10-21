/**
 * Deal Evaluator Component - "Where & When" Flow
 *
 * Allows users to select a destination and month, then evaluates:
 * - Is this a good deal right now?
 * - When is the best time to book?
 *
 * Returns BUY/TRACK/WAIT recommendation with baseline comparison
 * and optimal booking window.
 */

import { useState } from 'react';
import {
  evaluateDeal,
  DealEvaluation,
  getRecommendationColor,
  getRecommendationBadge,
  formatDelta,
  getDealScoreColor
} from '@/lib/dealsApi';

const MONTHS = [
  { n: 1, label: 'Jan' },
  { n: 2, label: 'Feb' },
  { n: 3, label: 'Mar' },
  { n: 4, label: 'Apr' },
  { n: 5, label: 'May' },
  { n: 6, label: 'Jun' },
  { n: 7, label: 'Jul' },
  { n: 8, label: 'Aug' },
  { n: 9, label: 'Sep' },
  { n: 10, label: 'Oct' },
  { n: 11, label: 'Nov' },
  { n: 12, label: 'Dec' }
];

export interface DealEvaluatorProps {
  defaultOrigin?: string;
  defaultDest?: string;
  defaultMonth?: number;
  className?: string;
}

export function DealEvaluator({
  defaultOrigin = 'JFK',
  defaultDest = 'MIA',
  defaultMonth = new Date().getMonth() + 1,
  className = ''
}: DealEvaluatorProps) {
  const [origin, setOrigin] = useState(defaultOrigin);
  const [dest, setDest] = useState(defaultDest);
  const [month, setMonth] = useState<number>(defaultMonth);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DealEvaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck() {
    if (!dest || dest.length !== 3) {
      setError('Please enter a valid 3-letter destination code');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const evaluation = await evaluateDeal(origin, dest, month, 'economy');
      setResult(evaluation);
    } catch (e: any) {
      setError(e.message || 'Failed to evaluate deal');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const delta = formatDelta(result?.delta_pct);

  return (
    <div className={`rounded-lg border border-ink-500 bg-ink-700 p-6 ${className}`}>
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-xl font-bold text-text-prim mb-1">Where & When</h3>
        <p className="text-sm text-text-dim">
          Check if now is a good time to book, or when you should wait
        </p>
      </div>

      {/* Input Controls */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        {/* Origin */}
        <div>
          <label className="block text-sm text-text-dim mb-1">From</label>
          <input
            className="bg-ink-900 border border-ink-500 rounded px-3 py-2 w-24 text-text-prim font-mono uppercase"
            value={origin}
            onChange={(e) => setOrigin(e.target.value.toUpperCase().slice(0, 3))}
            maxLength={3}
            placeholder="JFK"
          />
        </div>

        {/* Destination */}
        <div>
          <label className="block text-sm text-text-dim mb-1">To</label>
          <input
            className="bg-ink-900 border border-ink-500 rounded px-3 py-2 w-24 text-text-prim font-mono uppercase"
            value={dest}
            onChange={(e) => setDest(e.target.value.toUpperCase().slice(0, 3))}
            maxLength={3}
            placeholder="MIA"
          />
        </div>

        {/* Month Selector */}
        <div className="flex-1">
          <label className="block text-sm text-text-dim mb-1">Depart Month</label>
          <div className="flex gap-1 flex-wrap">
            {MONTHS.map((m) => (
              <button
                key={m.n}
                onClick={() => setMonth(m.n)}
                className={`px-3 py-1 rounded border text-sm transition-colors ${
                  month === m.n
                    ? 'bg-text-prim text-ink-900 border-text-prim font-semibold'
                    : 'border-ink-500 text-text-dim hover:bg-ink-600 hover:text-text-prim'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Check Button */}
        <button
          onClick={handleCheck}
          disabled={loading || !dest}
          className="px-6 py-2 rounded bg-text-prim text-ink-900 font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {loading ? 'Checking...' : 'Check Deal'}
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded bg-glow-magenta/10 border border-glow-magenta p-3 mb-4">
          <p className="text-glow-magenta text-sm">Error: {error}</p>
        </div>
      )}

      {/* Results */}
      {result && result.has_data && (
        <div className="mt-6 space-y-4">
          {/* Recommendation Card */}
          <div className="rounded-lg bg-ink-900 p-4 border border-ink-500">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-sm text-text-dim mb-1">Recommendation</div>
                <div
                  className={`text-3xl font-bold font-flap ${getRecommendationColor(
                    result.recommendation
                  )}`}
                >
                  {result.recommendation}
                </div>
                <div className="text-xs text-text-dim mt-1">
                  {result.confidence}% confidence
                </div>
              </div>

              {result.deal_score !== undefined && (
                <div className="text-right">
                  <div className="text-sm text-text-dim mb-1">Deal Score</div>
                  <div className={`text-2xl font-bold ${getDealScoreColor(result.deal_score)}`}>
                    {result.deal_score}
                  </div>
                  <div className="text-xs text-text-dim">out of 100</div>
                </div>
              )}
            </div>

            {result.rationale && (
              <p className="text-sm text-text-dim border-t border-ink-700 pt-3">
                {result.rationale}
              </p>
            )}
          </div>

          {/* Price Comparison Grid */}
          <div className="grid gap-3 sm:grid-cols-3">
            {/* Current Price */}
            <div className="rounded bg-ink-900 p-4 border border-ink-500">
              <div className="text-sm text-text-dim mb-1">Current Price</div>
              <div className="text-2xl font-bold text-text-prim">
                ${result.current_price?.toFixed(0)}
              </div>
              <div className={`text-sm ${delta.color} mt-1`}>
                {delta.text} vs median
              </div>
            </div>

            {/* Baseline */}
            {result.baseline && (
              <div className="rounded bg-ink-900 p-4 border border-ink-500">
                <div className="text-sm text-text-dim mb-2">30-Day Baseline</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-text-dim">P25 (Low):</span>
                    <span className="text-text-prim font-mono">
                      ${result.baseline.p25.toFixed(0)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-dim">P50 (Median):</span>
                    <span className="text-text-prim font-mono font-semibold">
                      ${result.baseline.p50.toFixed(0)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-dim">P75 (High):</span>
                    <span className="text-text-prim font-mono">
                      ${result.baseline.p75.toFixed(0)}
                    </span>
                  </div>
                  <div className="flex justify-between text-text-dim border-t border-ink-700 pt-1 mt-1">
                    <span>Samples:</span>
                    <span>{result.baseline.samples}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Best Time to Book */}
            <div className="rounded bg-ink-900 p-4 border border-ink-500">
              <div className="text-sm text-text-dim mb-1">Best Time to Book</div>
              {result.sweet_spot ? (
                <>
                  <div className="text-xl font-bold text-text-prim">
                    {result.sweet_spot.min_days}–{result.sweet_spot.max_days} days
                  </div>
                  <div className="text-xs text-text-dim mt-1">before departure</div>
                </>
              ) : (
                <div className="text-sm text-text-dim italic">
                  Not enough curve data yet
                </div>
              )}
            </div>
          </div>

          {/* Route Info */}
          <div className="text-xs text-text-dim text-center">
            {origin} → {dest} • {MONTHS[month - 1].label} {new Date().getFullYear()} •{' '}
            {result.baseline?.samples || 0} price samples in last 30 days
          </div>
        </div>
      )}

      {/* No Data State */}
      {result && !result.has_data && (
        <div className="rounded bg-ink-900 border border-ink-500 p-4 text-center">
          <p className="text-text-dim mb-2">{result.message}</p>
          <p className="text-sm text-text-dim">
            Try another month or destination, or check back later.
          </p>
        </div>
      )}
    </div>
  );
}
