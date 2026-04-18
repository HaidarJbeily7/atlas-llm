import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useExperimentData } from '../hooks/useExperimentData';
import LoadingSpinner from '../components/LoadingSpinner';
// data utilities
import clsx from 'clsx';

export default function Compliance() {
  const { summary, models, loading } = useExperimentData();

  const articleMap = useMemo(() => {
    if (!summary) return [];
    const map = new Map<string, {
      article_id: string;
      title: string;
      models: Record<string, { status: string; findings: number; critical: number }>;
    }>();

    for (const entry of summary.compliance) {
      const existing = map.get(entry.article_id) ?? {
        article_id: entry.article_id,
        title: entry.title,
        models: {},
      };
      existing.models[entry.model_short] = {
        status: entry.status,
        findings: (existing.models[entry.model_short]?.findings ?? 0) + entry.findings_count,
        critical: (existing.models[entry.model_short]?.critical ?? 0) + entry.critical_findings,
      };
      map.set(entry.article_id, existing);
    }
    return Array.from(map.values());
  }, [summary]);

  if (loading || !summary) return <LoadingSpinner />;

  const complianceData = models.map((m) => {
    const modelScans = summary.scans.filter((s) => s.model === m.model);
    const totalArticles = modelScans.reduce((s, sc) => s + sc.compliance_assessment.articles_assessed, 0);
    const passedArticles = modelScans.reduce((s, sc) => s + sc.compliance_assessment.articles_passed, 0);
    return {
      model: m.modelShort,
      passed: passedArticles,
      failed: totalArticles - passedArticles,
    };
  });

  const criticalData = models.map((m) => {
    const modelScans = summary.scans.filter((s) => s.model === m.model);
    let critical = 0;
    for (const scan of modelScans) {
      critical += scan.security_score.vulnerabilities_by_severity.critical ?? 0;
    }
    return { model: m.modelShort, critical };
  });

  const allModelNames = models.map((m) => m.modelShort);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Compliance Assessment</h1>
        <p className="text-gray-500 mt-1">EU AI Act & OWASP LLM Top 10 compliance analysis</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Article Compliance by Model</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={complianceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="model" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="passed" fill="#22c55e" name="Passed" stackId="a" />
              <Bar dataKey="failed" fill="#ef4444" name="Failed" stackId="a" radius={[4, 4, 0, 0]} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Critical Findings per Model</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={criticalData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="model" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="critical" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="text-lg font-semibold text-white mb-4">Compliance Heatmap</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-3 px-4 text-gray-400 font-medium">Article</th>
              <th className="text-left py-3 px-4 text-gray-400 font-medium">Title</th>
              {allModelNames.map((m) => (
                <th key={m} className="text-center py-3 px-4 text-gray-400 font-medium">{m}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {articleMap.map((article) => (
              <tr key={article.article_id} className="border-b border-gray-800/50">
                <td className="py-3 px-4 text-white font-mono text-xs">{article.article_id}</td>
                <td className="py-3 px-4 text-gray-300">{article.title}</td>
                {allModelNames.map((model) => {
                  const data = article.models[model];
                  if (!data) return <td key={model} className="py-3 px-4 text-center text-gray-600">-</td>;
                  return (
                    <td key={model} className="py-3 px-4 text-center">
                      <span className={clsx(
                        'inline-flex items-center justify-center w-20 py-1 rounded text-xs font-medium',
                        data.status === 'compliant' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                      )}>
                        {data.status === 'compliant' ? 'PASS' : `${data.critical} crit`}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Recommendations</h2>
        <div className="space-y-3">
          {summary.scans.slice(0, 5).flatMap((scan) =>
            scan.recommendations.map((rec, i) => (
              <div key={`${scan.scan_id}-${i}`} className="flex gap-3 text-sm">
                <span className="text-amber-500 flex-shrink-0">!</span>
                <div>
                  <span className="text-gray-400 font-mono text-xs">{scan.model_short}</span>
                  <p className="text-gray-300 mt-0.5">{rec}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
