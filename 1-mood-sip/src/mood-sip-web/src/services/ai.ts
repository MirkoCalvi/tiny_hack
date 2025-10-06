import { API_BASE_URL, DEFAULT_MODEL } from '../config';
import type { MoodAnalysis } from '../types';

export async function checkBackendHealth(): Promise<{ ok: boolean; data?: any }>
{
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) return { ok: false };
    const data = await response.json();
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}

export async function analyzeWithOllama(base64Image: string, metadata?: any): Promise<MoodAnalysis> {
  const response = await fetch(`${API_BASE_URL}/analyze-mood`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: base64Image, model: DEFAULT_MODEL, ...(metadata && { metadata }) }),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return response.json();
}
