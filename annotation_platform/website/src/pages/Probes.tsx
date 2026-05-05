import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useExperimentData } from '../hooks/useExperimentData';
import LoadingSpinner from '../components/LoadingSpinner';
import StatCard from '../components/StatCard';
import { getProbeLabel, CHART_COLORS } from '../lib/data';

export default function Probes() {
  const { summary, models, loading } = useExperimentData();

  if (loading || !summary) return <LoadingSpinner />;

  const cc = summary.cascade_card;
  const probeList = summary.probes.map((p) => {
    // Use review-corrected stats from cascade_card when available
    const reviewed = cc?.per_condition?.[p.probe_name];
    const total = reviewed ? reviewed.total : p.passed + p.failed;
    const asr = reviewed ? reviewed.asr : (total > 0 ? (p.failed / total) * 100 : 0);
    const passRate = reviewed ? reviewed.refusal_rate : (total > 0 ? (p.passed / total) * 100 : 0);
    return {
      ...p,
      total_attempts: total,
      label: getProbeLabel(p.probe_name),
      asr,
      passRate,
      awcs: reviewed?.awcs ?? null,
      judge_agreement_rate: reviewed?.judge_agreement_rate ?? null,
    };
  });

  const groupedData = probeList.map((p) => {
    const row: Record<string, unknown> = { probe: p.label };
    for (const [model, data] of Object.entries(p.models)) {
      row[model] = data.pass_rate;
    }
    return row;
  });
  const allModels = [...new Set(models.map((m) => m.modelShort))];

  // Compute avg latency from findings_index
  const probeLatency = new Map<string, { total: number; count: number }>();
  for (const f of summary.findings_index) {
    const existing = probeLatency.get(f.probe) ?? { total: 0, count: 0 };
    if (f.latency_ms > 0) {
      existing.total += f.latency_ms;
      existing.count++;
    }
    probeLatency.set(f.probe, existing);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Probe Analysis</h1>
        <p className="text-gray-500 mt-1">Detailed breakdown by attack probe type</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {probeList.map((p) => (
          <StatCard
            key={p.probe_name}
            label={p.label}
            value={`${p.asr.toFixed(1)}% ASR`}
            sub={p.awcs !== null ? `AWCS: ${p.awcs.toFixed(3)}` : `${p.total_attempts} attempts`}
            trend={p.asr > 30 ? 'down' : 'up'}
          />
        ))}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Pass Rate: Model x Probe</h2>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={groupedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="probe" tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
            {allModels.map((model, i) => (
              <Bar key={model} dataKey={model} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[2, 2, 0, 0]} />
            ))}
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="text-lg font-semibold text-white mb-4">Probe Details</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-3 px-4 text-gray-400 font-medium">Probe</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">AWCS</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Reviewed</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Refusal</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">ASR</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Agreement</th>
              <th className="text-right py-3 px-4 text-gray-400 font-medium">Avg Latency</th>
            </tr>
          </thead>
          <tbody>
            {probeList.map((p) => {
              const lat = probeLatency.get(p.probe_name);
              return (
                <tr key={p.probe_name} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-3 px-4 text-white font-medium">{p.label}</td>
                  <td className={`py-3 px-4 text-right font-mono ${(p.awcs ?? 0) >= 0.2 ? 'text-green-400' : (p.awcs ?? 0) >= 0 ? 'text-amber-400' : 'text-red-400'}`}>
                    {p.awcs !== null ? p.awcs.toFixed(3) : '-'}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-300">{p.total_attempts}</td>
                  <td className="py-3 px-4 text-right text-green-400">{p.passRate.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right text-red-400 font-medium">{p.asr.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-right text-gray-300">{p.judge_agreement_rate !== null ? `${p.judge_agreement_rate}%` : '-'}</td>
                  <td className="py-3 px-4 text-right text-gray-300">
                    {lat && lat.count > 0 ? `${(lat.total / lat.count / 1000).toFixed(1)}s` : '-'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
