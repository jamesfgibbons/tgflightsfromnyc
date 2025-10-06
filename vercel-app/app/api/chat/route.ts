import { z } from 'zod';
import { streamText, StreamingTextResponse } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { createXai } from '@ai-sdk/xai';

export const runtime = 'edge';

const provider = (process.env.AI_PROVIDER || 'openai').toLowerCase();
const openai = createOpenAI({ apiKey: process.env.OPENAI_API_KEY });
const xai = createXai({ apiKey: process.env.XAI_API_KEY });

const model = provider === 'xai' ? xai.chat('grok-beta') : openai.chat('gpt-4o-mini');

const tools = {
  getRoutes: {
    description: 'Fetch canonical NYC routes (JFK/LGA/EWR).',
    parameters: z.object({}),
    execute: async () => {
      const r = await fetch(`${process.env.BACKEND_BASE_URL}/api/travel/routes_nyc`);
      return await r.json();
    },
  },
  getPriceQuotes: {
    description: 'Fetch parsed price quotes for a route.',
    parameters: z.object({ origin: z.string(), destination: z.string() }),
    execute: async ({ origin, destination }: { origin: string; destination: string }) => {
      const qs = new URLSearchParams({ origin, destination });
      const r = await fetch(`${process.env.BACKEND_BASE_URL}/api/travel/price_quotes?${qs}`);
      return await r.json();
    },
  },
  getBoardFeed: {
    description: 'Fetch split‑flap board rows for keywords/entities/overall.',
    parameters: z.object({ target: z.enum(['keywords', 'entities', 'overall']).default('keywords'), limit: z.number().default(8) }),
    execute: async ({ target, limit }: { target: 'keywords' | 'entities' | 'overall'; limit: number }) => {
      const qs = new URLSearchParams({ target, limit: String(limit) });
      const r = await fetch(`${process.env.BACKEND_BASE_URL}/api/board/feed?${qs}`);
      return await r.json();
    },
  },
  searchWeb: {
    description: 'Use Grok websearch to summarize recent sources with citations.',
    parameters: z.object({ query: z.string(), maxCitations: z.number().default(5) }),
    execute: async ({ query, maxCitations }: { query: string; maxCitations: number }) => {
      const qs = new URLSearchParams({ q: query, max_citations: String(maxCitations) });
      const r = await fetch(`${process.env.BACKEND_BASE_URL}/api/llm/grok_search?${qs}`);
      return await r.json();
    },
  },
};

export async function POST(req: Request) {
  const body = await req.json();
  const messages = body?.messages ?? [];

  const system = `You are Deal Composer, a VibeNet assistant. Use tools to fetch NYC routes, price quotes, board data, and web context (searchWeb via Grok). Summarize deals and recommend actions. Cite tool calls inline (e.g., [routes], [quotes], [board], [web]).`;

  const result = await streamText({ model, tools, system, messages });
  return new StreamingTextResponse(result.toAIStream());
}
