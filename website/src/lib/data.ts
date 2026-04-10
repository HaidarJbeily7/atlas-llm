import type { Manifest, ScanResult, ModelSummary, Finding } from '../types';

let cachedManifest: Manifest | null = null;
const scanCache = new Map<string, ScanResult>();

export async function loadManifest(): Promise<Manifest> {
  if (cachedManifest) return cachedManifest;
  const res = await fetch('/data/manifest.json');
  cachedManifest = await res.json();
  return cachedManifest!;
}

export async function loadScan(path: string): Promise<ScanResult> {
  const cached = scanCache.get(path);
  if (cached) return cached;
  const res = await fetch(`/data/${path}`);
  const data = await res.json();
  scanCache.set(path, data);
  return data;
}

export async function loadAllScans(): Promise<ScanResult[]> {
  const manifest = await loadManifest();
  const experiment = manifest.experiments[0];
  const scans = await Promise.all(
    experiment.scans.map((s) => loadScan(s.file))
  );
  return scans;
}

export function shortModelName(model: string): string {
  const parts = model.split('/');
  return parts[parts.length - 1];
}

export function aggregateByModel(scans: ScanResult[]): ModelSummary[] {
  const byModel = new Map<string, ScanResult[]>();

  for (const scan of scans) {
    const existing = byModel.get(scan.model_name) ?? [];
    existing.push(scan);
    byModel.set(scan.model_name, existing);
  }

  const summaries: ModelSummary[] = [];

  for (const [model, modelScans] of byModel) {
    let totalAttempts = 0;
    let totalPassed = 0;
    let totalFailed = 0;
    let totalCost = 0;
    let totalTokens = 0;
    let totalLatency = 0;
    let latencyCount = 0;
    const probes: Record<string, import('../types').ProbeResult> = {};

    for (const scan of modelScans) {
      totalCost += scan.total_cost_usd;
      totalTokens += scan.total_target_tokens + scan.total_attacker_tokens;

      for (const [probeName, probeResult] of Object.entries(scan.probe_results)) {
        totalAttempts += probeResult.total_attempts;
        totalPassed += probeResult.passed;
        totalFailed += probeResult.failed;
        probes[probeName] = probeResult;

        for (const finding of probeResult.findings) {
          if (finding.attempt.latency_ms > 0) {
            totalLatency += finding.attempt.latency_ms;
            latencyCount++;
          }
        }
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
      avgLatency: latencyCount > 0 ? totalLatency / latencyCount : 0,
      riskLevel: lastScan.security_score.risk_level,
      complianceStatus: lastScan.compliance_assessment.overall_status,
      securityScore: lastScan.security_score.overall_score,
    });
  }

  return summaries.sort((a, b) => b.overallPassRate - a.overallPassRate);
}

export function getAllFindings(scans: ScanResult[]): Finding[] {
  const findings: Finding[] = [];
  for (const scan of scans) {
    for (const probeResult of Object.values(scan.probe_results)) {
      findings.push(...probeResult.findings);
    }
  }
  return findings;
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
