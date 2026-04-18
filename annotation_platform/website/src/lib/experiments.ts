// Persisted-experiments API client.

import { authedFetch } from './auth';

export interface ExperimentMeta {
  id: string;
  timestamp: string;
  models: string[];
  conditions: string[];
  finding_count: number;
  created_at: string;
  updated_at: string;
}

export interface SeedResult {
  experiment_id: string;
  timestamp: string;
  findings_seeded: number;
  findings_missing: string[];
  source_dir: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authedFetch(path, init);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function listExperiments(): Promise<ExperimentMeta[]> {
  return req('/api/experiments');
}

export function deleteExperiment(id: string): Promise<void> {
  return req(`/api/experiments/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function seedExperiments(path: string, recursive = false): Promise<SeedResult[]> {
  return req('/api/experiments/seed', {
    method: 'POST',
    body: JSON.stringify({ path, recursive }),
  });
}
