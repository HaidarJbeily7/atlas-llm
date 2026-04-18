import type { Summary, ScanSummary, ModelAggregation, FindingDetail } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

// Currently-selected experiment id (null = latest). Setter invalidates caches.
let activeExperimentId: string | null = null;
let cachedSummary: Summary | null = null;
let findingCache = new Map<string, FindingDetail>();

const EXPERIMENT_CHANGE_EVENT = 'atlas:experiment-change';

export function setActiveExperiment(id: string | null): void {
  if (activeExperimentId === id) return;
  activeExperimentId = id;
  cachedSummary = null;
  findingCache = new Map();
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(EXPERIMENT_CHANGE_EVENT, { detail: id }));
  }
}

export function subscribeActiveExperiment(cb: (id: string | null) => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const handler = (e: Event) => cb((e as CustomEvent<string | null>).detail);
  window.addEventListener(EXPERIMENT_CHANGE_EVENT, handler);
  return () => window.removeEventListener(EXPERIMENT_CHANGE_EVENT, handler);
}

export function getActiveExperiment(): string | null {
  return activeExperimentId;
}

async function tryFetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function loadSummary(): Promise<Summary> {
  if (cachedSummary) return cachedSummary;
  // Prefer the DB-backed API; fall back to the static file when the backend isn't running.
  const apiUrl = activeExperimentId
    ? `${API_BASE}/api/experiments/${encodeURIComponent(activeExperimentId)}`
    : `${API_BASE}/api/summary`;
  const apiData = await tryFetchJson<Summary>(apiUrl);
  if (apiData) {
    cachedSummary = apiData;
    return apiData;
  }
  const res = await fetch('/data/summary.json');
  cachedSummary = await res.json();
  return cachedSummary!;
}

export async function loadFindingDetail(id: string): Promise<FindingDetail> {
  const cached = findingCache.get(id);
  if (cached) return cached;
  const apiUrl = activeExperimentId
    ? `${API_BASE}/api/experiments/${encodeURIComponent(activeExperimentId)}/findings/${encodeURIComponent(id)}`
    : `${API_BASE}/api/findings/${encodeURIComponent(id)}`;
  const apiData = await tryFetchJson<FindingDetail>(apiUrl);
  if (apiData) {
    findingCache.set(id, apiData);
    return apiData;
  }
  const res = await fetch(`/data/findings/${id}.json`);
  const data = await res.json();
  findingCache.set(id, data);
  return data;
}

export function shortModelName(model: string): string {
  const parts = model.split('/');
  return parts[parts.length - 1];
}

export function aggregateByModel(scans: ScanSummary[]): ModelAggregation[] {
  const byModel = new Map<string, ScanSummary[]>();

  for (const scan of scans) {
    const existing = byModel.get(scan.model) ?? [];
    existing.push(scan);
    byModel.set(scan.model, existing);
  }

  const summaries: ModelAggregation[] = [];

  for (const [model, modelScans] of byModel) {
    let totalAttempts = 0;
    let totalPassed = 0;
    let totalFailed = 0;
    let totalCost = 0;
    let totalTokens = 0;
    const probes: Record<string, import('../types').ProbeResultSummary> = {};

    for (const scan of modelScans) {
      totalCost += scan.total_cost_usd;
      totalTokens += scan.total_target_tokens + scan.total_attacker_tokens;

      for (const [probeName, pr] of Object.entries(scan.probe_results_summary)) {
        totalAttempts += pr.total_attempts;
        totalPassed += pr.passed;
        totalFailed += pr.failed;
        probes[probeName] = pr;
      }
    }

    const lastScan = modelScans[modelScans.length - 1];

    summaries.push({
      model,
      modelShort: shortModelName(model),
      probes,
      overallPassRate: totalAttempts > 0 ? (totalPassed / totalAttempts) * 100 : 0,
      totalAttempts,
      totalPassed,
      totalFailed,
      totalCost,
      totalTokens,
      avgLatency: 0, // computed from findings_index if needed
      riskLevel: lastScan.security_score.risk_level,
      complianceStatus: lastScan.compliance_assessment.overall_status,
      securityScore: lastScan.security_score.overall_score,
    });
  }

  return summaries.sort((a, b) => b.overallPassRate - a.overallPassRate);
}

export function getProbeLabel(probe: string): string {
  const labels: Record<string, string> = {
    jailbreak: 'Jailbreak (Static Single-Turn)',
    scripted_multi_turn: 'Scripted Multi-Turn',
    adaptive_single_turn: 'Adaptive Single-Turn',
    adaptive_multi_turn: 'Adaptive Multi-Turn',
  };
  return labels[probe] ?? probe;
}

export function getRiskColor(level: string): string {
  switch (level) {
    case 'critical': return '#ef4444';
    case 'high': return '#f97316';
    case 'medium': return '#f59e0b';
    case 'low': return '#22c55e';
    default: return '#6b7280';
  }
}

export const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
  '#f59e0b', '#22c55e', '#14b8a6', '#3b82f6',
];

export const PROBE_COLORS: Record<string, string> = {
  jailbreak: '#6366f1',
  scripted_multi_turn: '#8b5cf6',
  adaptive_single_turn: '#f59e0b',
  adaptive_multi_turn: '#ef4444',
};
