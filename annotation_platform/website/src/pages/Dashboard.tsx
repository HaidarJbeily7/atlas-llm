import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { Shield, AlertTriangle, DollarSign, Zap } from 'lucide-react';
import { useExperimentData } from '../hooks/useExperimentData';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import { getProbeLabel, CHART_COLORS } from '../lib/data';

export default function Dashboard() {
  const { summary, models, loading } = useExperimentData();

  if (loading || !summary) return <LoadingSpinner />;

  const totalAttempts = models.reduce((s, m) => s + m.totalAttempts, 0);
  const totalFailed = models.reduce((s, m) => s + m.totalFailed, 0);
  const totalCost = models.reduce((s, m) => s + m.totalCost, 0);
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

      <div className="grid grid-cols-4 gap-4">
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
          label="Total Cost"
          value={`$${totalCost.toFixed(2)}`}
          sub={`${models.length} models evaluated`}
          icon={<DollarSign className="w-5 h-5" />}
        />
        <StatCard
          label="Models Tested"
          value={models.length}
          sub={`${summary.scans.length} total scans`}
          icon={<Zap className="w-5 h-5" />}
        />
      </div>

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
                <Radar key={m.model} name={m.modelShort} dataKey={m.modelShort}
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
    </div>
  );
}
