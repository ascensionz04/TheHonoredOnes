import type { AppliedMove, Meta, Screen } from "./types"

// Same-origin in production (Vercel routes /api/py/* to api/index.py);
// proxied to uvicorn on port 8000 in development (see next.config.ts).
const BASE = "/api/py"

export class ApiError extends Error {}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { signal })
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err
    throw new ApiError("The engine could not be reached. Check your connection and try again.")
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(body?.detail ?? "Demo data could not be loaded. Choose another day or press Reset.")
  }
  return res.json() as Promise<T>
}

export function fetchMeta(signal?: AbortSignal) {
  return getJson<Meta>("/meta", signal)
}

export function screenKey(day: string, clock: number, moves: AppliedMove[], selected: string) {
  const params = new URLSearchParams({ day, clock: String(clock) })
  if (moves.length) params.set("actions", moves.map((m) => `${m.id}@${m.at}`).join(","))
  if (selected) params.set("selected", selected)
  return `/screen?${params.toString()}`
}

// Screens never change for the same inputs, so keep every one we have seen.
const cache = new Map<string, Promise<Screen>>()

export function fetchScreen(key: string): Promise<Screen> {
  let hit = cache.get(key)
  if (!hit) {
    hit = getJson<Screen>(key)
    cache.set(key, hit)
    hit.catch(() => cache.delete(key))
  }
  return hit
}
