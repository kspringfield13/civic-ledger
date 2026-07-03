// Thin API client. Base URL comes from env; defaults to local backend.
const BASE =
  (import.meta as any).env?.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export interface RiskSignal {
  id: number;
  detector_id: string;
  hypothesis: string;
  severity: number;
  confidence: number;
  status: string;
  disclaimer: string;
}
