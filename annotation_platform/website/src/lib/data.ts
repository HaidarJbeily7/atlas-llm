import type { Summary, ScanSummary, ModelAggregation, FindingDetail } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

// Currently-selected experiment id (null = latest). Setter invalidates caches.
let activeExperimentId: string | null = null;
let cachedSummary: Summary | null = null;
let cachedSummaryAt = 0;
const SUMMARY_TTL_MS = 180_000; // 3 minutes
let findingCache = new Map<string, FindingDetail>();

const EXPERIMENT_CHANGE_EVENT = 'atlas:experiment-change';

export function setActiveExperiment(id: string | null): void {
  if (activeExperimentId === id) return;
  activeExperimentId = id;
  cachedSummary = null;
  cachedSummaryAt = 0;
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

export async function loadSummary(): Promise<Summary> {
  if (cachedSummary && Date.now() - cachedSummaryAt < SUMMARY_TTL_MS) {
    return cachedSummary;
  }
  const apiUrl = activeExperimentId
    ? `${API_BASE}/api/experiments/${encodeURIComponent(activeExperimentId)}`
    : `${API_BASE}/api/summary`;
  const res = await fetch(apiUrl);
  if (!res.ok) {
    throw new Error(`Failed to load summary: ${res.status} ${res.statusText}`);
  }
  const data = (await res.json()) as Summary;
  cachedSummary = data;
  cachedSummaryAt = Date.now();
  return data;
}

export async function loadFindingDetail(id: string): Promise<FindingDetail> {
  const cached = findingCache.get(id);
  if (cached) return cached;
  const apiUrl = activeExperimentId
    ? `${API_BASE}/api/experiments/${encodeURIComponent(activeExperimentId)}/findings/${encodeURIComponent(id)}`
    : `${API_BASE}/api/findings/${encodeURIComponent(id)}`;
  const res = await fetch(apiUrl);
  if (!res.ok) {
    throw new Error(`Failed to load finding: ${res.status} ${res.statusText}`);
  }
  const data = (await res.json()) as FindingDetail;
  findingCache.set(id, data);
  return data;
}

export function formatCost(usd: number): string {
  if (usd === 0) return '$0.00';
  const abs = Math.abs(usd);
  if (abs >= 1) return `$${usd.toFixed(2)}`;
  if (abs >= 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(6)}`;
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
    let totalTargetCost = 0;
    let totalAttackerCost = 0;
    let totalTokens = 0;
    const probes: Record<string, import('../types').ProbeResultSummary> = {};

    for (const scan of modelScans) {
      totalCost += scan.total_cost_usd;
      totalTargetCost += scan.total_target_cost_usd ?? 0;
      totalAttackerCost += scan.total_attacker_cost_usd ?? 0;
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
      totalTargetCost,
      totalAttackerCost,
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
    jailbreak: 'Jailbreak (Static)',
    scripted_multi_turn: 'Scripted Multi-Turn',
    adaptive_single_query_st: 'Adaptive Single-Query ST',
    adaptive_single_turn: 'Adaptive Multi-Query ST',
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
  adaptive_single_query_st: '#3b82f6',
  adaptive_single_turn: '#f59e0b',
  adaptive_multi_turn: '#ef4444',
};
