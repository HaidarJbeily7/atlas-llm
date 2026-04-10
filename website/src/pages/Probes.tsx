import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useExperimentData } from '../hooks/useExperimentData';
import LoadingSpinner from '../components/LoadingSpinner';
import StatCard from '../components/StatCard';
import { getProbeLabel, CHART_COLORS, shortModelName } from '../lib/data';

export default function Probes() {
  const { scans, models, loading } = useExperimentData();

  if (loading) return <LoadingSpinner />;

  // Aggregate by probe
  const probeStats = new Map<string, {
    totalAttempts: number;
    passed: number;
    failed: number;
    totalCost: number;
    totalLatency: number;
    latencyCount: number;
    modelBreakdown: Map<string, { passed: number; failed: number; passRate: number }>;
  }>();

  for (const scan of scans) {
    for (const [probe, result] of Object.entries(scan.probe_results)) {
      const existing = probeStats.get(probe) ?? {
        totalAttempts: 0, passed: 0, failed: 0,
        totalCost: 0, totalLatency: 0, latencyCount: 0,
        modelBreakdown: new Map(),
      };
      existing.totalAttempts += result.total_attempts;
      existing.passed += result.passed;
      existing.failed += result.failed;

      const modelKey = shortModelName(scan.model_name);
      existing.modelBreakdown.set(modelKey, {
        passed: result.passed,
        failed: result.failed,
        passRate: result.pass_rate,
      });

      for (const f of result.findings) {
        existing.totalCost += f.attempt.cost_usd;
        if (f.attempt.latency_ms > 0) {
          existing.totalLatency += f.attempt.latency_ms;
          existing.latencyCount++;
        }
      }

      probeStats.set(probe, existing);
    }
  }

  const probeList = Array.from(probeStats.entries()).map(([probe, stats]) => ({
    probe,
    label: getProbeLabel(probe),
    asr: stats.totalAttempts > 0 ? (stats.failed / stats.totalAttempts) * 100 : 0,
    passRate: stats.totalAttempts > 0 ? (stats.passed / stats.totalAttempts) * 100 : 0,
    ...stats,
  }));

  // Grouped bar: per probe, per model
  const groupedData = probeList.map((p) => {
    const row: Record<string, unknown> = { probe: p.label };
    for (const [model, data] of p.modelBreakdown) {
      row[model] = data.passRate;
    }
    return row;
  });
  const allModels = [...new Set(models.map((m) => m.modelShort))];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Probe Analysis</h1>
        <p className="text-gray-500 mt-1">Detailed breakdown by attack probe type</p>
      </div>

      {/* Probe stat cards */}
      <div className="grid grid-cols-4 gap-4">
        {probeList.map((p) => (
          <StatCard
            key={p.probe}
            label={p.label}
            value={`${p.asr.toFixed(1)}% ASR`}
            sub={`${p.failed}/${p.totalAttempts} attacks succeeded`}
            trend={p.asr > 30 ? 'down' : 'up'}
          />
        ))}
      </div>

      {/* Model pass rates per probe */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Pass Rate: Model x Probe</h2>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={groupedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="probe" tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
              labelStyle={{ color: '#fff' }}
            />
            {allModels.map((model, i) => (
              <Bar
                key={model}
                dataKey={model}
                fill={CHART_COLORS[i % CHART_COLORS.length]}
                radius={[2, 2, 0, 0]}
              />
            ))}
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Probe details table */}
      <div className="card overflow-x-auto">
        <h2 className="text-lg font-semibold text-white mb-4">Probe Details</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-3 px-4 text-gray-400 font-medium">Probe</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Attempts</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Passed</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Failed</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Pass Rate</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">ASR</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Avg Latency</th>
            </tr>
          </thead>
          <tbody>
            {probeList.map((p) => (
              <tr key={p.probe} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-3 px-4 text-white font-medium">{p.label}</td>
                <td className="py-3 px-4 text-right text-gray-300">{p.totalAttempts}</td>
                <td className="py-3 px-4 text-right text-green-400">{p.passed}</td>
                <td className="py-3 px-4 text-right text-red-400">{p.failed}</td>
                <td className="py-3 px-4 text-right text-white font-medium">{p.passRate.toFixed(1)}%</td>
                <td className="py-3 px-4 text-right text-amber-400 font-medium">{p.asr.toFixed(1)}%</td>
                <td className="py-3 px-4 text-right text-gray-300">
                  {p.latencyCount > 0 ? `${(p.totalLatency / p.latencyCount / 1000).toFixed(1)}s` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
