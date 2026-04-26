import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useExperimentData } from '../hooks/useExperimentData';
import ScoreBar from '../components/ScoreBar';
import LoadingSpinner from '../components/LoadingSpinner';
import { getProbeLabel, formatCost, PROBE_COLORS } from '../lib/data';
import clsx from 'clsx';

export default function Models() {
  const { summary, models, loading } = useExperimentData();

  if (loading || !summary) return <LoadingSpinner />;

  const probeNames = [...new Set(models.flatMap((m) => Object.keys(m.probes)))];
  const heatmapData = models.map((m) => {
    const row: Record<string, unknown> = { model: m.modelShort };
    for (const probe of probeNames) {
      row[probe] = m.probes[probe]?.pass_rate ?? null;
    }
    return row;
  });

  const costData = models.map((m) => ({
    name: m.modelShort,
    targetCost: m.totalTargetCost,
    attackerCost: m.totalAttackerCost,
    tokens: m.totalTokens,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Model Comparison</h1>
        <p className="text-gray-500 mt-1">Side-by-side analysis across all tested models</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {models.map((m) => (
          <div key={m.model} className="card">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-white">{m.modelShort}</h3>
                <p className="text-xs text-gray-500 font-mono">{m.model}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={clsx('badge', {
                  'badge-success': m.riskLevel === 'low',
                  'badge-warning': m.riskLevel === 'medium',
                  'badge-danger': m.riskLevel === 'high' || m.riskLevel === 'critical',
                })}>{m.riskLevel} risk</span>
                <span className={clsx('badge', {
                  'badge-success': m.complianceStatus === 'compliant',
                  'badge-danger': m.complianceStatus === 'non-compliant',
                })}>{m.complianceStatus}</span>
              </div>
            </div>

            <div className="grid grid-cols-5 gap-4 mb-4">
              <div>
                <p className="text-xs text-gray-500">Pass Rate</p>
                <p className="text-xl font-bold text-white">{m.overallPassRate.toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Attempts</p>
                <p className="text-xl font-bold text-white">{m.totalAttempts}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Failed</p>
                <p className="text-xl font-bold text-red-400">{m.totalFailed}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Target Cost</p>
                <p className="text-xl font-bold text-white">{formatCost(m.totalTargetCost)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Attacker Cost</p>
                <p className="text-xl font-bold text-purple-300">{formatCost(m.totalAttackerCost)}</p>
              </div>
            </div>

            <div className="space-y-2">
              {Object.entries(m.probes).map(([probe, result]) => (
                <ScoreBar key={probe} label={getProbeLabel(probe)} value={result.pass_rate} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Pass Rate Comparison by Probe</h2>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={heatmapData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="model" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
            {probeNames.map((probe) => (
              <Bar key={probe} dataKey={probe} name={getProbeLabel(probe)}
                fill={PROBE_COLORS[probe] ?? '#6b7280'} radius={[2, 2, 0, 0]} />
            ))}
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Cost per Model ($)</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={costData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis dataKey="name" type="category" width={120} tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
              formatter={(value) => formatCost(Number(value ?? 0))}
            />
            <Bar dataKey="targetCost" stackId="cost" fill="#6366f1" name="Target Cost" />
            <Bar dataKey="attackerCost" stackId="cost" fill="#a855f7" name="Attacker Cost" radius={[0, 4, 4, 0]} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
