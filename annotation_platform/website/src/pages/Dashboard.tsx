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

  // Severity pie
  const severityCounts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const scan of summary.scans) {
    const vulns = scan.security_score.vulnerabilities_by_severity;
    for (const [sev, count] of Object.entries(vulns)) {
      if (sev in severityCounts) severityCounts[sev] += count;
    }
  }
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

      {/* Review progress & reviewed-only stats */}
      {backendOk && reviewStats && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <ClipboardCheck className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-semibold text-white">Review Progress</h2>
          </div>
          <div className="grid grid-cols-6 gap-4 mb-4">
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
            <div>
              <p className="text-xs text-gray-500">False Positives</p>
              <p className="text-xl font-bold text-green-400">{reviewStats.false_positive}</p>
              {reviewStats.reviewed > 0 && (
                <p className="text-xs text-gray-500">
                  {((reviewStats.false_positive / reviewStats.reviewed) * 100).toFixed(1)}% of reviewed
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
                    <td className="py-2 pr-4 text-right font-semibold text-amber-400">{c.adj_asr}%</td>
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

      {/* ── RQ2: Failure-Type Distribution (confirmed only) ── */}
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
                <p className="text-xs text-gray-500">Fail rates and judge accuracy from human annotations (confirmed verdict vs judge error)</p>
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
                        <th className="pb-1 pr-1 text-right">Fail Rate</th>
                        <th className="pb-1 pr-1 text-right">Accuracy</th>
                        <th className="pb-1 pr-2 text-right">Error Rate</th>
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
                            <td className="py-2 pr-1 text-right text-amber-400">{s.fail_rate}%</td>
                            <td className="py-2 pr-1 text-right text-green-400">
                              {s.reviewed > 0 ? `${s.accuracy}%` : '-'}
                            </td>
                            <td className="py-2 pr-2 text-right text-red-400">
                              {s.reviewed > 0 ? `${s.error_rate}%` : '-'}
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
              Accuracy = confirmed verdicts / reviewed findings. Error Rate = judge errors / reviewed findings. Unreviewed findings are not counted.
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
