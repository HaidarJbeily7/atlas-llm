import { Fragment } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { Shield, AlertTriangle, DollarSign, Zap, ClipboardCheck, Crosshair, Activity, FlaskConical, Bug, Radar } from 'lucide-react';
import { useExperimentData } from '../hooks/useExperimentData';
import { useReviewData } from '../hooks/useReviewData';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import { getProbeLabel, formatCost, CHART_COLORS } from '../lib/data';
import type { CascadeConditionCard } from '../types';

export default function Dashboard() {
  const { summary, models, loading } = useExperimentData();
  const { reviewStats, backendOk } = useReviewData();

  if (loading || !summary) return <LoadingSpinner />;

  const totalAttempts = models.reduce((s, m) => s + m.totalAttempts, 0);
  const totalFailed = models.reduce((s, m) => s + m.totalFailed, 0);
  const totalTargetCost = models.reduce((s, m) => s + m.totalTargetCost, 0);
  const totalAttackerCost = models.reduce((s, m) => s + m.totalAttackerCost, 0);
  const overallPassRate = totalAttempts > 0 ? ((totalAttempts - totalFailed) / totalAttempts) * 100 : 0;

  // Model comparison chart data
  const modelChartData = models.map((m) => ({
    name: m.modelShort,
    'Pass Rate': Number(m.overallPassRate.toFixed(1)),
  }));

  // Probe breakdown
  const probeChartData = summary.probes.map((p) => ({
    probe: getProbeLabel(p.probe_name),
    probeKey: p.probe_name,
    passed: p.passed,
    failed: p.failed,
    asr: Number(((p.failed / (p.passed + p.failed)) * 100).toFixed(1)),
  }));

  // Radar data per model
  const radarData = probeChartData.map((p) => {
    const entry: Record<string, unknown> = { probe: p.probe.replace(/\(.*\)/, '').trim() };
    for (const model of models) {
      const pr = model.probes[p.probeKey];
      entry[model.modelShort] = pr ? Number(pr.pass_rate.toFixed(1)) : 0;
    }
    return entry;
  });

  // Severity pie — use cascade card (review-corrected) if available
  const severityCounts: Record<string, number> = summary.cascade_card?.severity_distribution
    ? { ...{ critical: 0, high: 0, medium: 0, low: 0 }, ...summary.cascade_card.severity_distribution }
    : (() => {
        const raw: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
        for (const scan of summary.scans) {
          const vulns = scan.security_score.vulnerabilities_by_severity;
          for (const [sev, count] of Object.entries(vulns)) {
            if (sev in raw) raw[sev] += count;
          }
        }
        return raw;
      })();
  const severityData = Object.entries(severityCounts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));
  const sevColors: Record<string, string> = {
    critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#22c55e',
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Experiment Dashboard</h1>
        <p className="text-gray-500 mt-1">2x2 Factorial Experiment — {models.length} models, {probeChartData.length} probe types</p>
        <div className="flex flex-wrap gap-3 mt-2 text-xs">
          <span className="bg-purple-900/30 border border-purple-800/40 text-purple-300 rounded px-2 py-1">
            Attacker: deepseek-r1-0528
          </span>
          <span className="bg-blue-900/30 border border-blue-800/40 text-blue-300 rounded px-2 py-1">
            Judge 1: openai/gpt-4o-mini
          </span>
          <span className="bg-emerald-900/30 border border-emerald-800/40 text-emerald-300 rounded px-2 py-1">
            Judge 2: google/gemini-2.5-flash
          </span>
          <span className="bg-amber-900/30 border border-amber-800/40 text-amber-300 rounded px-2 py-1">
            Judge 3: anthropic/claude-4.5-haiku
          </span>
          <span className="bg-gray-800 border border-gray-700 text-gray-400 rounded px-2 py-1">
            Voting: majority (2/3)
          </span>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <StatCard
          label="Overall Pass Rate"
          value={`${overallPassRate.toFixed(1)}%`}
          sub={`${totalAttempts} total attempts`}
          icon={<Shield className="w-5 h-5" />}
        />
        <StatCard
          label="Attack Success Rate"
          value={`${((totalFailed / totalAttempts) * 100).toFixed(1)}%`}
          sub={`${totalFailed} successful attacks`}
          trend="down"
          icon={<AlertTriangle className="w-5 h-5" />}
        />
        <StatCard
          label="Target Cost"
          value={formatCost(totalTargetCost)}
          sub="target model spend"
          icon={<DollarSign className="w-5 h-5" />}
        />
        <StatCard
          label="Attacker Cost"
          value={formatCost(totalAttackerCost)}
          sub="attacker model spend"
          icon={<Crosshair className="w-5 h-5" />}
        />
        <StatCard
          label="Models Tested"
          value={models.length}
          sub={`${summary.scans.length} total scans`}
          icon={<Zap className="w-5 h-5" />}
        />
      </div>

      {/* Cascade Card */}
      {summary.cascade_card && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">Cascade Card</h2>
            {summary.cascade_card.unreviewed > 0 && (
              <span className="text-xs text-amber-400 ml-2">
                {summary.cascade_card.unreviewed} unreviewed excluded
              </span>
            )}
            <span className="text-xs text-gray-500 ml-auto">AWCS adapted from RAHS (arxiv:2603.10807)</span>
          </div>
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div>
              <p className="text-xs text-gray-500">AWCS Score</p>
              <p className={`text-2xl font-bold ${summary.cascade_card.awcs >= 0.2 ? 'text-green-400' : summary.cascade_card.awcs >= 0 ? 'text-amber-400' : 'text-red-400'}`}>
                {summary.cascade_card.awcs.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500">range: -0.6 to 0.5</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Refusal Rate</p>
              <p className="text-2xl font-bold text-green-400">{summary.cascade_card.refusal_rate}%</p>
              <p className="text-xs text-gray-500">attacks properly refused</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Judge Agreement</p>
              <p className={`text-2xl font-bold ${summary.cascade_card.judge_agreement_rate >= 80 ? 'text-green-400' : 'text-amber-400'}`}>
                {summary.cascade_card.judge_agreement_rate}%
              </p>
              <p className="text-xs text-gray-500">3/3 judges agree</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Critical Damage</p>
              <p className={`text-2xl font-bold ${summary.cascade_card.critical_damage_rate > 5 ? 'text-red-400' : 'text-amber-400'}`}>
                {summary.cascade_card.critical_damage_rate}%
              </p>
              <p className="text-xs text-gray-500">critical severity failures</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Severity</p>
              <div className="flex gap-1 mt-1">
                {Object.entries(summary.cascade_card.severity_distribution || {}).map(([sev, count]) => (
                  <span
                    key={sev}
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      sev === 'critical' ? 'bg-red-900/50 text-red-300' :
                      sev === 'high' ? 'bg-orange-900/50 text-orange-300' :
                      sev === 'medium' ? 'bg-amber-900/50 text-amber-300' :
                      'bg-green-900/50 text-green-300'
                    }`}
                  >
                    {sev}: {count as number}
                  </span>
                ))}
              </div>
            </div>
          </div>
          {/* Per-condition breakdown */}
          {summary.cascade_card.per_condition && Object.keys(summary.cascade_card.per_condition).length > 0 && (
            <div className="overflow-x-auto mb-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">By Condition (aggregated)</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                    <th className="pb-2 pr-4">Condition</th>
                    <th className="pb-2 pr-4 text-right">AWCS</th>
                    <th className="pb-2 pr-4 text-right">ASR</th>
                    <th className="pb-2 pr-4 text-right">Refusal</th>
                    <th className="pb-2 pr-4 text-right">Agreement</th>
                    <th className="pb-2 pr-4 text-right">Critical</th>
                    <th className="pb-2 text-right">N</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary.cascade_card.per_condition).map(([cond, stats]: [string, CascadeConditionCard]) => (
                    <tr key={cond} className="border-b border-gray-800/50">
                      <td className="py-2 pr-4 text-gray-200 font-medium">{getProbeLabel(cond)}</td>
                      <td className={`py-2 pr-4 text-right font-mono ${stats.awcs >= 0.2 ? 'text-green-400' : stats.awcs >= 0 ? 'text-amber-400' : 'text-red-400'}`}>{stats.awcs?.toFixed(3) ?? '-'}</td>
                      <td className="py-2 pr-4 text-right text-red-400">{stats.asr}%</td>
                      <td className="py-2 pr-4 text-right text-green-400">{stats.refusal_rate}%</td>
                      <td className="py-2 pr-4 text-right text-gray-300">{stats.judge_agreement_rate}%</td>
                      <td className="py-2 pr-4 text-right text-red-300">{stats.critical_damage_rate}%</td>
                      <td className="py-2 text-right text-gray-400">{stats.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {/* Per-condition × per-model heatmap */}
          {summary.cascade_card.per_condition_model && Object.keys(summary.cascade_card.per_condition_model).length > 0 && (() => {
            const pcm = summary.cascade_card!.per_condition_model;
            const conditions = Object.keys(pcm);
            const allModels = new Set<string>();
            for (const cond of conditions) {
              for (const m of Object.keys(pcm[cond])) allModels.add(m);
            }
            const modelList = Array.from(allModels).sort();

            return (
              <div className="overflow-x-auto">
                <h3 className="text-sm font-medium text-gray-400 mb-2">ASR Heatmap — Condition × Model</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                      <th className="pb-2 pr-3">Condition</th>
                      {modelList.map((m) => (
                        <th key={m} className="pb-2 px-2 text-center">{m}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {conditions.map((cond) => (
                      <tr key={cond} className="border-b border-gray-800/50">
                        <td className="py-2 pr-3 text-gray-200 font-medium text-xs">{getProbeLabel(cond)}</td>
                        {modelList.map((m) => {
                          const stats = pcm[cond]?.[m];
                          if (!stats) return <td key={m} className="py-2 px-2 text-center text-gray-600">-</td>;
                          const asr = stats.asr;
                          const bg = asr >= 80 ? 'bg-red-900/60' :
                                     asr >= 50 ? 'bg-orange-900/50' :
                                     asr >= 20 ? 'bg-amber-900/40' :
                                     'bg-green-900/40';
                          const text = asr >= 80 ? 'text-red-200' :
                                       asr >= 50 ? 'text-orange-200' :
                                       asr >= 20 ? 'text-amber-200' :
                                       'text-green-200';
                          return (
                            <td key={m} className={`py-2 px-2 text-center text-xs font-mono rounded ${bg} ${text}`}>
                              {asr}%
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })()}
          {/* Per-model AWCS */}
          {summary.cascade_card.per_model && Object.keys(summary.cascade_card.per_model).length > 0 && (
            <div className="overflow-x-auto mt-6">
              <h3 className="text-sm font-medium text-gray-400 mb-2">AWCS by Model</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                    <th className="pb-2 pr-4">Model</th>
                    <th className="pb-2 pr-4 text-right">AWCS</th>
                    <th className="pb-2 pr-4 text-right">ASR</th>
                    <th className="pb-2 pr-4 text-right">Refusal</th>
                    <th className="pb-2 pr-4 text-right">Agreement</th>
                    <th className="pb-2 pr-4 text-right">Critical</th>
                    <th className="pb-2 text-right">N</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary.cascade_card.per_model)
                    .sort(([,a]: [string, CascadeConditionCard], [,b]: [string, CascadeConditionCard]) => b.awcs - a.awcs)
                    .map(([model, stats]: [string, CascadeConditionCard]) => (
                    <tr key={model} className="border-b border-gray-800/50">
                      <td className="py-2 pr-4 text-gray-200 font-medium">{model}</td>
                      <td className={`py-2 pr-4 text-right font-mono ${stats.awcs >= 0.2 ? 'text-green-400' : stats.awcs >= 0 ? 'text-amber-400' : 'text-red-400'}`}>
                        {stats.awcs.toFixed(3)}
                      </td>
                      <td className="py-2 pr-4 text-right text-red-400">{stats.asr}%</td>
                      <td className="py-2 pr-4 text-right text-green-400">{stats.refusal_rate}%</td>
                      <td className="py-2 pr-4 text-right text-gray-300">{stats.judge_agreement_rate}%</td>
                      <td className="py-2 pr-4 text-right text-red-300">{stats.critical_damage_rate}%</td>
                      <td className="py-2 text-right text-gray-400">{stats.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* SOTA Baselines Comparison */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Radar className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-white">SOTA Baselines Comparison</h2>
          <span className="text-xs text-gray-500 ml-auto">Literature ASR numbers for context</span>
        </div>
        <div className="grid grid-cols-2 gap-6">
          {/* PAIR baselines */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">
              PAIR — Single-Turn Adaptive
              <a href="https://arxiv.org/abs/2310.08419" target="_blank" rel="noopener" className="text-cyan-500 hover:text-cyan-400 ml-1">[Chao 2023]</a>
              <a href="https://arxiv.org/abs/2404.02151" target="_blank" rel="noopener" className="text-cyan-500 hover:text-cyan-400 ml-1">[ICLR 2025]</a>
            </h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="pb-1.5 text-left">Model</th>
                  <th className="pb-1.5 text-right">Lit. ASR</th>
                  <th className="pb-1.5 text-right">Our ASR</th>
                  <th className="pb-1.5 text-right">Delta</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                {([
                  { model: 'GPT-3.5 Turbo', lit: 60 as number | null, ours: null as number | null },
                  { model: 'GPT-4 Turbo', lit: 33, ours: null },
                  { model: 'GPT-4o', lit: null, ours: summary.cascade_card?.per_condition_model?.['adaptive_single_turn']?.['gpt-4o']?.asr ?? null },
                  { model: 'GPT-4o-mini', lit: null, ours: summary.cascade_card?.per_condition_model?.['adaptive_single_turn']?.['gpt-4o-mini']?.asr ?? null },
                  { model: 'Claude 2.0', lit: 4, ours: null },
                  { model: 'Claude Sonnet 4', lit: null, ours: summary.cascade_card?.per_condition_model?.['adaptive_single_turn']?.['claude-sonnet-4']?.asr ?? null },
                  { model: 'Llama-2 70B', lit: 15, ours: null },
                  { model: 'Llama 3.3 70B', lit: null, ours: summary.cascade_card?.per_condition_model?.['adaptive_single_turn']?.['llama-3.3-70b-instruct']?.asr ?? null },
                ]).map((row, i) => (
                  <tr key={i} className="border-b border-gray-800/30">
                    <td className="py-1 text-gray-200">{row.model}</td>
                    <td className="py-1 text-right">{row.lit !== null ? `${row.lit}%` : <span className="text-gray-600">—</span>}</td>
                    <td className="py-1 text-right">{row.ours !== null ? <span className="text-amber-400">{row.ours}%</span> : <span className="text-gray-600">—</span>}</td>
                    <td className="py-1 text-right">
                      {row.lit !== null && row.ours !== null
                        ? <span className={row.ours > row.lit ? 'text-red-400' : 'text-green-400'}>{row.ours > row.lit ? '+' : ''}{(row.ours - row.lit).toFixed(0)}%</span>
                        : <span className="text-gray-600">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[10px] text-gray-600 mt-2">Our attacker: DeepSeek-R1 (reasoning model) vs GPT-4 in original PAIR</p>
          </div>

          {/* Multi-turn & Autonomous baselines */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">
              Autonomous Attackers
              <a href="https://www.nature.com/articles/s41467-026-69010-1" target="_blank" rel="noopener" className="text-cyan-500 hover:text-cyan-400 ml-1">[Nature 2026]</a>
              <a href="https://arxiv.org/abs/2404.01833" target="_blank" rel="noopener" className="text-cyan-500 hover:text-cyan-400 ml-1">[USENIX 2025]</a>
            </h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="pb-1.5 text-left">Model</th>
                  <th className="pb-1.5 text-right">Nature 2026</th>
                  <th className="pb-1.5 text-right">Multi-Turn</th>
                  <th className="pb-1.5 text-right">Multi-Query ST</th>
                  <th className="pb-1.5 text-right">Single-Query ST</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                {[
                  { model: 'Claude Sonnet 4', nature: 2.86, ourKey: 'claude-sonnet-4' },
                  { model: 'GPT-4o', nature: 61.43, ourKey: 'gpt-4o' },
                  { model: 'GPT-4o-mini', nature: 34.29, ourKey: 'gpt-4o-mini' },
                  { model: 'Llama 3.x 70B', nature: 32.86, ourKey: 'llama-3.3-70b-instruct' },
                  { model: 'Gemini Flash', nature: 71.43, ourKey: 'gemini-2.5-flash' },
                  { model: 'DeepSeek V3', nature: 90.0, ourKey: 'deepseek-chat-v3-0324' },
                  { model: 'Qwen 72B', nature: 71.43, ourKey: 'qwen-2.5-72b-instruct' },
                ].map((row, i) => {
                  const mt = summary.cascade_card?.per_condition_model?.['adaptive_multi_turn']?.[row.ourKey]?.asr ?? null;
                  const mq = summary.cascade_card?.per_condition_model?.['adaptive_single_turn']?.[row.ourKey]?.asr ?? null;
                  const sq = summary.cascade_card?.per_condition_model?.['adaptive_single_query_st']?.[row.ourKey]?.asr ?? null;
                  return (
                    <tr key={i} className="border-b border-gray-800/30">
                      <td className="py-1 text-gray-200">{row.model}</td>
                      <td className="py-1 text-right">{row.nature}%</td>
                      <td className="py-1 text-right">{mt !== null ? <span className="text-amber-400">{mt}%</span> : <span className="text-gray-600">—</span>}</td>
                      <td className="py-1 text-right">{mq !== null ? <span className="text-red-400">{mq}%</span> : <span className="text-gray-600">—</span>}</td>
                      <td className="py-1 text-right">{sq !== null ? <span className="text-blue-400">{sq}%</span> : <span className="text-gray-600">—</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="text-[10px] text-gray-600 mt-2">Nature 2026: max harm score % with reasoning model attackers (97.14% overall)</p>
          </div>
        </div>

        {/* Key references */}
        <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-gray-800">
          {[
            { label: 'PAIR', url: 'https://arxiv.org/abs/2310.08419', tag: 'Chao 2023' },
            { label: 'TAP', url: 'https://arxiv.org/abs/2312.02119', tag: 'Mehrotra 2023' },
            { label: 'HarmBench', url: 'https://arxiv.org/abs/2402.04249', tag: 'ICLR 2025' },
            { label: 'Adaptive Attacks', url: 'https://arxiv.org/abs/2404.02151', tag: 'ICLR 2025' },
            { label: 'JailbreakBench', url: 'https://arxiv.org/abs/2404.01318', tag: 'NeurIPS 2024' },
            { label: 'Crescendo', url: 'https://arxiv.org/abs/2404.01833', tag: 'USENIX 2025' },
            { label: 'Autonomous Jailbreak', url: 'https://www.nature.com/articles/s41467-026-69010-1', tag: 'Nature 2026' },
            { label: 'RAHS / AWCS', url: 'https://arxiv.org/abs/2603.10807', tag: 'arxiv 2026' },
          ].map((ref) => (
            <a key={ref.label} href={ref.url} target="_blank" rel="noopener"
              className="text-[10px] bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-400 hover:text-cyan-400 hover:border-cyan-800 transition-colors">
              {ref.label} <span className="text-gray-600">({ref.tag})</span>
            </a>
          ))}
        </div>
      </div>

      {/* Review progress & reviewed-only stats */}
      {backendOk && reviewStats && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <ClipboardCheck className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-semibold text-white">Review Progress</h2>
          </div>
          <div className="grid grid-cols-4 md:grid-cols-8 gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500">Reviewed</p>
              <p className="text-xl font-bold text-white">
                {reviewStats.reviewed} / {reviewStats.total}
              </p>
              <p className="text-xs text-gray-500">
                {reviewStats.total > 0 ? ((reviewStats.reviewed / reviewStats.total) * 100).toFixed(0) : 0}% complete
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Needs Review</p>
              <p className="text-xl font-bold text-amber-400">{reviewStats.needs_review}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Confirmed Vulnerabilities</p>
              <p className="text-xl font-bold text-red-400">{reviewStats.confirmed}</p>
              {reviewStats.reviewed > 0 && (
                <p className="text-xs text-gray-500">
                  {((reviewStats.confirmed / reviewStats.reviewed) * 100).toFixed(1)}% of reviewed
                </p>
              )}
            </div>
            <div title="Judges said PASS and human agrees — model properly refused the attack">
              <p className="text-xs text-gray-500">Confirmed Safe</p>
              <p className="text-xl font-bold text-emerald-400">{reviewStats.confirmed_safe ?? 0}</p>
              {reviewStats.reviewed > 0 && (
                <p className="text-xs text-gray-500">
                  {(((reviewStats.confirmed_safe ?? 0) / reviewStats.reviewed) * 100).toFixed(1)}% of reviewed
                </p>
              )}
            </div>
            <div title="Judges said FAIL but human says model was actually safe — judges were wrong">
              <p className="text-xs text-gray-500">False Positives</p>
              <p className="text-xl font-bold text-green-400">{reviewStats.false_positive}</p>
              {reviewStats.reviewed > 0 && (
                <p className="text-xs text-gray-500">
                  {((reviewStats.false_positive / reviewStats.reviewed) * 100).toFixed(1)}% of reviewed
                </p>
              )}
            </div>
            <div title="Judges said PASS but human says attack actually succeeded — judges missed it">
              <p className="text-xs text-gray-500">False Negatives</p>
              <p className="text-xl font-bold text-purple-400">{reviewStats.false_negative ?? 0}</p>
              {reviewStats.reviewed > 0 && (
                <p className="text-xs text-gray-500">
                  {(((reviewStats.false_negative ?? 0) / reviewStats.reviewed) * 100).toFixed(1)}% of reviewed
                </p>
              )}
            </div>
            <div>
              <p className="text-xs text-gray-500">Reviewed Pass Rate</p>
              <p className="text-xl font-bold text-white">
                {reviewStats.reviewed_pass_rate !== null ? `${reviewStats.reviewed_pass_rate.toFixed(1)}%` : '-'}
              </p>
              <p className="text-xs text-gray-500">
                {reviewStats.reviewed_pass_count} pass / {reviewStats.reviewed_fail_count} fail
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Confirmed Vuln Rate</p>
              <p className="text-xl font-bold text-red-300">
                {reviewStats.reviewed > 0
                  ? `${((reviewStats.confirmed / reviewStats.reviewed) * 100).toFixed(1)}%`
                  : '-'}
              </p>
              <p className="text-xs text-gray-500">of reviewed findings</p>
            </div>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
            <div
              className="h-full rounded-full transition-all bg-indigo-500"
              style={{ width: `${reviewStats.total > 0 ? (reviewStats.reviewed / reviewStats.total) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Detector Performance */}
      {summary.detector_stats && summary.detector_stats.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-semibold text-white">Detector Performance</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                  <th className="pb-2 pr-4">Detector</th>
                  <th className="pb-2 pr-4 text-right">Evaluated</th>
                  <th className="pb-2 pr-4 text-right">Passed</th>
                  <th className="pb-2 pr-4 text-right">Failed</th>
                  <th className="pb-2 pr-4 text-right">Fail Rate</th>
                  <th className="pb-2 text-right">Avg Score</th>
                </tr>
              </thead>
              <tbody>
                {summary.detector_stats.map((d) => (
                  <tr key={d.name} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-200 font-medium">{d.name}</td>
                    <td className="py-2 pr-4 text-right text-gray-400">{d.total}</td>
                    <td className="py-2 pr-4 text-right text-green-400">{d.passed}</td>
                    <td className="py-2 pr-4 text-right text-red-400">{d.failed}</td>
                    <td className="py-2 pr-4 text-right text-amber-400">
                      {d.total > 0 ? ((d.failed / d.total) * 100).toFixed(1) : 0}%
                    </td>
                    <td className="py-2 text-right text-gray-300">{d.avg_score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Model Pass Rates</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={modelChartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis dataKey="name" type="category" width={120} tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
              <Bar dataKey="Pass Rate" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Model Robustness Radar</h2>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="probe" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} />
              {models.map((m, i) => (
                <RechartsRadar key={m.model} name={m.modelShort} dataKey={m.modelShort}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  fill={CHART_COLORS[i % CHART_COLORS.length]} fillOpacity={0.1} />
              ))}
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="card col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">Attack Success Rate by Probe</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={probeChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="probe" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
              <Bar dataKey="passed" stackId="a" fill="#22c55e" name="Passed" />
              <Bar dataKey="failed" stackId="a" fill="#ef4444" name="Failed" radius={[4, 4, 0, 0]} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Findings by Severity</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={severityData} cx="50%" cy="50%" innerRadius={50} outerRadius={90} dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}>
                {severityData.map((entry) => (
                  <Cell key={entry.name} fill={sevColors[entry.name] ?? '#6b7280'} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── RQ1: Attack Budget & Cost Effectiveness ── */}
      {summary.condition_stats && summary.condition_stats.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <FlaskConical className="w-5 h-5 text-amber-400" />
            <div>
              <h2 className="text-lg font-semibold text-white">RQ1 — Attack Budget & Cost Effectiveness</h2>
              <p className="text-xs text-gray-500">Adjusted ASR = raw failures minus human-confirmed false positives (detector errors removed)</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                  <th className="pb-2 pr-4">Condition</th>
                  <th className="pb-2 pr-4 text-right">Attempts</th>
                  <th className="pb-2 pr-4 text-right">Adj. Failed</th>
                  <th className="pb-2 pr-4 text-right">FP Removed</th>
                  <th className="pb-2 pr-4 text-right">Adj. ASR</th>
                  <th className="pb-2 pr-4 text-right">Raw ASR</th>
                  <th className="pb-2 pr-4 text-right">Target Cost</th>
                  <th className="pb-2 pr-4 text-right">Attacker Cost</th>
                  <th className="pb-2 text-right">Cost / Attack</th>
                </tr>
              </thead>
              <tbody>
                {summary.condition_stats.map((c) => (
                  <tr key={c.condition} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-200 font-medium">{getProbeLabel(c.condition)}</td>
                    <td className="py-2 pr-4 text-right text-gray-400">{c.adj_total}</td>
                    <td className="py-2 pr-4 text-right text-red-400">{c.adj_failed}</td>
                    <td className="py-2 pr-4 text-right text-green-400">{c.false_positives}</td>
                    <td className="py-2 pr-4 text-right font-semibold text-amber-400">
                      {c.adj_asr}%
                      {c.adj_asr_ci && <span className="text-[10px] text-gray-500 ml-1">[{c.adj_asr_ci[0]}-{c.adj_asr_ci[1]}]</span>}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-500">{c.asr}%</td>
                    <td className="py-2 pr-4 text-right text-gray-300">{formatCost(c.target_cost)}</td>
                    <td className="py-2 pr-4 text-right text-purple-300">{formatCost(c.attacker_cost)}</td>
                    <td className="py-2 text-right text-amber-300">{c.adj_failed > 0 ? formatCost(c.cost_per_attack) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-gray-600 mt-2">
            Adj. ASR excludes findings where the judge was wrong (human-marked as false positive). Unreviewed findings trust the judge.
          </p>
          <div className="mt-4">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={summary.condition_stats.map((c) => ({
                name: getProbeLabel(c.condition).replace(/\(.*\)/, '').trim(),
                'Adjusted ASR': c.adj_asr,
                'Raw ASR': c.asr,
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} label={{ value: 'ASR %', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
                <Bar dataKey="Raw ASR" fill="#6b7280" name="Raw ASR %" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Adjusted ASR" fill="#f59e0b" name="Adjusted ASR %" radius={[4, 4, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── RQ2: Refinement Ablation ── */}
      {summary.refinement_ablation && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <FlaskConical className="w-5 h-5 text-blue-400" />
            <div>
              <h2 className="text-lg font-semibold text-white">RQ2 — Refinement Ablation: Single-Query vs Multi-Query PAIR</h2>
              <p className="text-xs text-gray-500">Paired comparison on {summary.refinement_ablation.n_pairs} matched intent×model pairs</p>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div>
              <p className="text-xs text-gray-500">Single-Query ASR</p>
              <p className="text-2xl font-bold text-blue-400">{summary.refinement_ablation.sq_asr}%</p>
              <p className="text-xs text-gray-500">[{summary.refinement_ablation.sq_asr_ci[0]}-{summary.refinement_ablation.sq_asr_ci[1]}%]</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Multi-Query ASR</p>
              <p className="text-2xl font-bold text-amber-400">{summary.refinement_ablation.mq_asr}%</p>
              <p className="text-xs text-gray-500">[{summary.refinement_ablation.mq_asr_ci[0]}-{summary.refinement_ablation.mq_asr_ci[1]}%]</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Refinement Gain</p>
              <p className="text-2xl font-bold text-green-400">+{summary.refinement_ablation.gain_pp}pp</p>
              <p className="text-xs text-gray-500">from iterative refinement</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">McNemar p-value</p>
              <p className="text-2xl font-bold text-red-400">{summary.refinement_ablation.mcnemar_p < 0.001 ? summary.refinement_ablation.mcnemar_p.toExponential(1) : summary.refinement_ablation.mcnemar_p.toFixed(4)}</p>
              <p className="text-xs text-gray-500">discordant: {summary.refinement_ablation.discordant_b}:{summary.refinement_ablation.discordant_c}</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <h3 className="text-sm font-medium text-gray-400 mb-2">Per-Model Refinement Gain</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                  <th className="pb-2 pr-4">Model</th>
                  <th className="pb-2 pr-4 text-right">Single-Query ASR</th>
                  <th className="pb-2 pr-4 text-right">Multi-Query ASR</th>
                  <th className="pb-2 pr-4 text-right">Gain</th>
                  <th className="pb-2 text-right">p-value</th>
                </tr>
              </thead>
              <tbody>
                {summary.refinement_ablation.per_model.sort((a, b) => b.gain_pp - a.gain_pp).map((m) => (
                  <tr key={m.model} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-200 font-medium">{m.model}</td>
                    <td className="py-2 pr-4 text-right text-blue-400">{m.sq_asr}%</td>
                    <td className="py-2 pr-4 text-right text-amber-400">{m.mq_asr}%</td>
                    <td className={`py-2 pr-4 text-right font-semibold ${m.gain_pp >= 20 ? 'text-green-400' : m.gain_pp >= 10 ? 'text-amber-400' : 'text-gray-400'}`}>+{m.gain_pp}pp</td>
                    <td className={`py-2 text-right ${m.p_value < 0.05 / 8 ? 'text-red-400 font-semibold' : 'text-gray-500'}`}>
                      {m.p_value < 0.001 ? m.p_value.toExponential(1) : m.p_value.toFixed(4)}
                      {m.p_value < 0.05 / 8 && ' *'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[10px] text-gray-600 mt-2">* significant after Bonferroni correction (p {'<'} 0.00625). McNemar exact test on paired intent×model outcomes.</p>
          </div>
        </div>
      )}

      {/* ── RQ6: Paired Statistical Comparisons ── */}
      {summary.paired_comparisons && summary.paired_comparisons.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-5 h-5 text-indigo-400" />
            <div>
              <h2 className="text-lg font-semibold text-white">Paired ASR Comparisons (McNemar)</h2>
              <p className="text-xs text-gray-500">All tests paired on the same 40 intents × 8 models. Bonferroni-corrected for {summary.paired_comparisons.length} comparisons.</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                  <th className="pb-2 pr-4">Condition A</th>
                  <th className="pb-2 pr-4">Condition B</th>
                  <th className="pb-2 pr-4 text-right">ASR A</th>
                  <th className="pb-2 pr-4 text-right">ASR B</th>
                  <th className="pb-2 pr-4 text-right">Difference</th>
                  <th className="pb-2 pr-4 text-right">p-value</th>
                  <th className="pb-2 text-right">Significant?</th>
                </tr>
              </thead>
              <tbody>
                {summary.paired_comparisons.map((pc, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-200">{getProbeLabel(pc.condition_a)}</td>
                    <td className="py-2 pr-4 text-gray-200">{getProbeLabel(pc.condition_b)}</td>
                    <td className="py-2 pr-4 text-right text-gray-300">{pc.asr_a}%</td>
                    <td className="py-2 pr-4 text-right text-gray-300">{pc.asr_b}%</td>
                    <td className={`py-2 pr-4 text-right font-semibold ${pc.diff_pp > 0 ? 'text-red-400' : pc.diff_pp < 0 ? 'text-green-400' : 'text-gray-400'}`}>
                      {pc.diff_pp > 0 ? '+' : ''}{pc.diff_pp}pp
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-400 font-mono text-xs">
                      {pc.p_value < 0.001 ? pc.p_value.toExponential(1) : pc.p_value.toFixed(4)}
                    </td>
                    <td className={`py-2 text-right font-semibold ${pc.significant ? 'text-green-400' : 'text-gray-600'}`}>
                      {pc.significant ? 'Yes' : 'No'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── RQ3: Failure-Type Distribution (confirmed only) ── */}
      {summary.failure_type_distribution && summary.failure_type_distribution.length > 0 && (() => {
        const allDetectors = [...new Set(summary.failure_type_distribution.flatMap((f) =>
          [...Object.keys(f.detector_failures), ...Object.keys(f.detector_failures_all)]
        ))];
        const ftData = summary.failure_type_distribution.map((f) => {
          const row: Record<string, unknown> = { condition: getProbeLabel(f.condition).replace(/\(.*\)/, '').trim() };
          for (const det of allDetectors) row[det] = f.detector_failures[det] ?? 0;
          return row;
        });
        const detColors = ['#ef4444', '#f97316', '#f59e0b', '#6366f1', '#8b5cf6', '#ec4899'];
        return (
          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <Bug className="w-5 h-5 text-red-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">RQ2 — Failure-Type Distribution</h2>
                <p className="text-xs text-gray-500">Detector flags on confirmed vulnerabilities only (false positives excluded)</p>
              </div>
            </div>
            <div className="overflow-x-auto mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                    <th className="pb-2 pr-4">Condition</th>
                    {allDetectors.map((d) => (
                      <th key={d} className="pb-2 pr-4 text-center" colSpan={2}>{d}</th>
                    ))}
                  </tr>
                  <tr className="text-left text-[10px] text-gray-600 border-b border-gray-800">
                    <th className="pb-1"></th>
                    {allDetectors.map((d) => (
                      <Fragment key={d}><th className="pb-1 pr-1 text-right">Confirmed</th><th className="pb-1 pr-2 text-right text-gray-700">Raw</th></Fragment>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {summary.failure_type_distribution.map((f) => (
                    <tr key={f.condition} className="border-b border-gray-800/50">
                      <td className="py-2 pr-4 text-gray-200 font-medium">{getProbeLabel(f.condition)}</td>
                      {allDetectors.map((d) => (
                        <Fragment key={d}>
                          <td className="py-2 pr-1 text-right text-red-400">{f.detector_failures[d] ?? 0}</td>
                          <td className="py-2 pr-2 text-right text-gray-600">{f.detector_failures_all[d] ?? 0}</td>
                        </Fragment>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={ftData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="condition" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
                {allDetectors.map((det, i) => (
                  <Bar key={det} dataKey={det} stackId="a" fill={detColors[i % detColors.length]} name={det}
                    radius={i === allDetectors.length - 1 ? [4, 4, 0, 0] : undefined} />
                ))}
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        );
      })()}

      {/* ── RQ3: Detector Sensitivity by Condition (with human review accuracy) ── */}
      {summary.detector_by_condition && summary.detector_by_condition.length > 0 && (() => {
        const conditions = [...new Set(summary.detector_by_condition.flatMap((d) => Object.keys(d.by_condition)))];
        return (
          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <Radar className="w-5 h-5 text-emerald-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">RQ3 — Detector Sensitivity by Condition</h2>
                <p className="text-xs text-gray-500">Fail rates, precision, recall, and F1 from human annotations</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                    <th className="pb-2 pr-4">Detector</th>
                    {conditions.map((c) => (
                      <th key={c} className="pb-2 pr-2 text-center" colSpan={3}>{getProbeLabel(c).replace(/\(.*\)/, '').trim()}</th>
                    ))}
                  </tr>
                  <tr className="text-left text-[10px] text-gray-600 border-b border-gray-800">
                    <th className="pb-1"></th>
                    {conditions.map((c) => (
                      <Fragment key={c}>
                        <th className="pb-1 pr-1 text-right">Precision</th>
                        <th className="pb-1 pr-1 text-right">Recall</th>
                        <th className="pb-1 pr-2 text-right">F1</th>
                      </Fragment>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {summary.detector_by_condition.map((d) => (
                    <tr key={d.detector} className="border-b border-gray-800/50">
                      <td className="py-2 pr-4 text-gray-200 font-medium">{d.detector}</td>
                      {conditions.map((c) => {
                        const s = d.by_condition[c];
                        if (!s) return (
                          <Fragment key={c}>
                            <td className="py-2 pr-1 text-right text-gray-600">-</td>
                            <td className="py-2 pr-1 text-right text-gray-600">-</td>
                            <td className="py-2 pr-2 text-right text-gray-600">-</td>
                          </Fragment>
                        );
                        return (
                          <Fragment key={c}>
                            <td className="py-2 pr-1 text-right text-blue-400">
                              {s.reviewed > 0 ? `${s.precision}%` : '-'}
                            </td>
                            <td className="py-2 pr-1 text-right text-green-400">
                              {s.reviewed > 0 ? `${s.recall}%` : '-'}
                            </td>
                            <td className="py-2 pr-2 text-right text-amber-400">
                              {s.reviewed > 0 ? `${s.f1}%` : '-'}
                            </td>
                          </Fragment>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[10px] text-gray-600 mt-2">
              Precision = TP / (TP + FP) — when the detector flags an attack, how often is it correct? Recall = TP / (TP + FN) — of all real attacks, how many does the detector catch? F1 = harmonic mean. Unreviewed findings are not counted.
            </p>
            {/* Sensitivity chart */}
            <div className="mt-4">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={summary.detector_by_condition.map((d) => {
                  const row: Record<string, unknown> = { detector: d.detector };
                  for (const c of conditions) {
                    row[getProbeLabel(c).replace(/\(.*\)/, '').trim()] = d.by_condition[c]?.fail_rate ?? 0;
                  }
                  return row;
                })}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="detector" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} label={{ value: 'Fail Rate %', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 11 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
                  {conditions.map((c, i) => (
                    <Bar key={c} dataKey={getProbeLabel(c).replace(/\(.*\)/, '').trim()}
                      fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[2, 2, 0, 0]} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
