import { useState, useMemo } from 'react';
import { useExperimentData } from '../hooks/useExperimentData';
import LoadingSpinner from '../components/LoadingSpinner';
import { getProbeLabel, shortModelName } from '../lib/data';
import type { Finding, ScanResult } from '../types';
import clsx from 'clsx';

interface EnrichedFinding extends Finding {
  model: string;
  modelShort: string;
}

function enrichFindings(scans: ScanResult[]): EnrichedFinding[] {
  const results: EnrichedFinding[] = [];
  for (const scan of scans) {
    for (const probeResult of Object.values(scan.probe_results)) {
      for (const finding of probeResult.findings) {
        results.push({
          ...finding,
          model: scan.model_name,
          modelShort: shortModelName(scan.model_name),
        });
      }
    }
  }
  return results;
}

export default function Findings() {
  const { scans, loading } = useExperimentData();
  const [filterPassed, setFilterPassed] = useState<'all' | 'passed' | 'failed'>('all');
  const [filterModel, setFilterModel] = useState<string>('all');
  const [filterProbe, setFilterProbe] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const PAGE_SIZE = 20;

  const allFindings = useMemo(() => enrichFindings(scans), [scans]);
  const modelNames = useMemo(() => [...new Set(allFindings.map((f) => f.model))], [allFindings]);
  const probeNames = useMemo(() => [...new Set(allFindings.map((f) => f.attempt.probe_name))], [allFindings]);

  const filtered = useMemo(() => {
    return allFindings.filter((f) => {
      if (filterPassed === 'passed' && !f.passed) return false;
      if (filterPassed === 'failed' && f.passed) return false;
      if (filterModel !== 'all' && f.model !== filterModel) return false;
      if (filterProbe !== 'all' && f.attempt.probe_name !== filterProbe) return false;
      return true;
    });
  }, [allFindings, filterPassed, filterModel, filterProbe]);

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Findings Explorer</h1>
        <p className="text-gray-500 mt-1">{allFindings.length} total findings across all scans</p>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-4 items-center">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Status</label>
          <select
            value={filterPassed}
            onChange={(e) => { setFilterPassed(e.target.value as 'all' | 'passed' | 'failed'); setPage(0); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200"
          >
            <option value="all">All</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Model</label>
          <select
            value={filterModel}
            onChange={(e) => { setFilterModel(e.target.value); setPage(0); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200"
          >
            <option value="all">All Models</option>
            {modelNames.map((m) => (
              <option key={m} value={m}>{shortModelName(m)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Probe</label>
          <select
            value={filterProbe}
            onChange={(e) => { setFilterProbe(e.target.value); setPage(0); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200"
          >
            <option value="all">All Probes</option>
            {probeNames.map((p) => (
              <option key={p} value={p}>{getProbeLabel(p)}</option>
            ))}
          </select>
        </div>
        <div className="ml-auto text-sm text-gray-400">
          Showing {filtered.length} findings
        </div>
      </div>

      {/* Findings list */}
      <div className="space-y-2">
        {paged.map((f) => (
          <div key={f.id} className="card !p-0 overflow-hidden">
            <button
              onClick={() => setExpandedId(expandedId === f.id ? null : f.id)}
              className="w-full text-left px-4 py-3 flex items-center gap-4 hover:bg-gray-800/50 transition-colors"
            >
              <span className={clsx(
                'w-2 h-2 rounded-full flex-shrink-0',
                f.passed ? 'bg-green-500' : 'bg-red-500'
              )} />
              <span className="text-sm font-medium text-white flex-1 truncate">
                {f.attempt.prompt.slice(0, 100)}...
              </span>
              {f.attempt.messages.length > 0 && (
                <span className="badge badge-warning text-[10px]">
                  {Math.ceil(f.attempt.messages.length / 2)} turns
                </span>
              )}
              {f.attempt.num_attacker_calls > 0 && (
                <span className="text-[10px] text-purple-400 font-medium">ADAPTIVE</span>
              )}
              <span className="badge badge-info text-xs">{f.modelShort}</span>
              <span className="text-xs text-gray-500">{getProbeLabel(f.attempt.probe_name)}</span>
              <span className={clsx('badge', f.passed ? 'badge-success' : 'badge-danger')}>
                {f.passed ? 'PASS' : 'FAIL'}
              </span>
            </button>

            {expandedId === f.id && (
              <div className="border-t border-gray-800 px-4 py-4 space-y-4">
                {/* Metadata row */}
                <div className="flex flex-wrap gap-3 text-xs">
                  <span className={clsx(
                    'badge',
                    f.severity === 'critical' && 'badge-danger',
                    f.severity === 'high' && 'badge-warning',
                    f.severity === 'medium' && 'badge-warning',
                    f.severity === 'low' && 'badge-success',
                  )}>{f.severity} severity</span>
                  {f.attempt.metadata.condition ? (
                    <span className="badge badge-info">
                      {String(f.attempt.metadata.condition)}
                    </span>
                  ) : null}
                  {f.attempt.metadata.objective ? (
                    <span className="text-gray-400 italic">
                      Objective: {String(f.attempt.metadata.objective).slice(0, 120)}
                    </span>
                  ) : null}
                </div>

                {/* Cost breakdown - target vs attacker */}
                <div className="grid grid-cols-6 gap-3">
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Target Cost</p>
                    <p className="text-sm font-semibold text-white">
                      ${(f.attempt.cost_usd - (f.attempt.num_attacker_calls > 0 ? f.attempt.cost_usd * f.attempt.attacker_tokens_in / Math.max(1, f.attempt.attacker_tokens_in + f.attempt.target_tokens_in) : 0)).toFixed(4)}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5">
                      {f.attempt.target_tokens_in} in / {f.attempt.target_tokens_out} out
                    </p>
                  </div>
                  <div className={clsx(
                    'rounded-lg p-3',
                    f.attempt.num_attacker_calls > 0 ? 'bg-purple-900/20 border border-purple-800/30' : 'bg-gray-800/50'
                  )}>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Attacker Cost</p>
                    <p className="text-sm font-semibold text-purple-300">
                      {f.attempt.num_attacker_calls > 0
                        ? `$${(f.attempt.cost_usd * f.attempt.attacker_tokens_in / Math.max(1, f.attempt.attacker_tokens_in + f.attempt.target_tokens_in)).toFixed(4)}`
                        : '-'}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5">
                      {f.attempt.attacker_tokens_in > 0
                        ? `${f.attempt.attacker_tokens_in} in / ${f.attempt.attacker_tokens_out} out`
                        : 'No attacker model'}
                    </p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Total Cost</p>
                    <p className="text-sm font-semibold text-white">${f.attempt.cost_usd.toFixed(4)}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Latency</p>
                    <p className="text-sm font-semibold text-white">{(f.attempt.latency_ms / 1000).toFixed(1)}s</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Target Calls</p>
                    <p className="text-sm font-semibold text-white">{f.attempt.num_target_calls}</p>
                  </div>
                  <div className={clsx(
                    'rounded-lg p-3',
                    f.attempt.num_attacker_calls > 0 ? 'bg-purple-900/20 border border-purple-800/30' : 'bg-gray-800/50'
                  )}>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Attacker Calls</p>
                    <p className="text-sm font-semibold text-purple-300">
                      {f.attempt.num_attacker_calls || '-'}
                    </p>
                  </div>
                </div>

                {/* Conversation thread (multi-turn) or prompt/response (single-turn) */}
                {f.attempt.messages.length > 0 ? (
                  <div>
                    <p className="text-xs text-gray-500 mb-2 font-medium">
                      Conversation ({f.attempt.messages.length} messages, {Math.ceil(f.attempt.messages.length / 2)} turns)
                    </p>
                    <div className="bg-gray-800/40 rounded-lg p-4 max-h-96 overflow-auto space-y-3">
                      {(f.attempt.messages as Array<{ role: string; content: string }>).map((msg, i) => (
                        <div
                          key={i}
                          className={clsx(
                            'flex gap-3',
                            msg.role === 'assistant' ? 'justify-start' : 'justify-end'
                          )}
                        >
                          <div
                            className={clsx(
                              'max-w-[80%] rounded-lg px-3 py-2 text-xs',
                              msg.role === 'assistant'
                                ? 'bg-gray-700/60 text-gray-200'
                                : 'bg-indigo-900/40 border border-indigo-800/30 text-indigo-100'
                            )}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className={clsx(
                                'text-[10px] font-semibold uppercase tracking-wider',
                                msg.role === 'assistant' ? 'text-green-400' : 'text-indigo-400'
                              )}>
                                {msg.role === 'assistant' ? 'Target Model' : 'Attacker'}
                              </span>
                              <span className="text-[10px] text-gray-600">Turn {Math.floor(i / 2) + 1}</span>
                            </div>
                            <pre className="whitespace-pre-wrap text-xs leading-relaxed">{msg.content}</pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1 font-medium">Prompt</p>
                      <pre className="text-xs text-gray-300 bg-gray-800 rounded-lg p-3 max-h-48 overflow-auto whitespace-pre-wrap">
                        {f.attempt.prompt}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1 font-medium">Response</p>
                      <pre className="text-xs text-gray-300 bg-gray-800 rounded-lg p-3 max-h-48 overflow-auto whitespace-pre-wrap">
                        {f.attempt.response}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Adaptive attack metadata */}
                {f.attempt.metadata.adaptivity === 'adaptive' && (
                  <div className="flex gap-4 text-xs bg-purple-900/10 border border-purple-800/20 rounded-lg px-4 py-2">
                    <span className="text-gray-500">PAIR Score: <span className="text-purple-300 font-medium">{String(f.attempt.metadata.pair_score ?? '-')}</span></span>
                    <span className="text-gray-500">Attack Successful: <span className={clsx('font-medium', f.attempt.metadata.attack_successful ? 'text-red-400' : 'text-green-400')}>{String(f.attempt.metadata.attack_successful ?? '-')}</span></span>
                    <span className="text-gray-500">Turns: <span className="text-purple-300 font-medium">{String(f.attempt.metadata.turns_completed ?? '-')}</span></span>
                    <span className="text-gray-500">Best Score: <span className="text-purple-300 font-medium">{String(f.attempt.metadata.best_score ?? '-')}</span></span>
                  </div>
                )}

                {/* Detector results */}
                <div>
                  <p className="text-xs text-gray-500 mb-2 font-medium">Detector Results</p>
                  <div className="grid grid-cols-3 gap-2">
                    {f.detector_results.map((d, i) => (
                      <div
                        key={i}
                        className={clsx(
                          'rounded-lg px-3 py-2 text-xs border',
                          d.passed
                            ? 'bg-green-900/20 border-green-800/50'
                            : 'bg-red-900/20 border-red-800/50'
                        )}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-medium text-gray-200">{d.detector_name}</span>
                          <span className={d.passed ? 'text-green-400' : 'text-red-400'}>
                            {d.passed ? 'PASS' : 'FAIL'}
                          </span>
                        </div>
                        <p className="text-gray-400 truncate">{d.evidence}</p>
                        <div className="flex gap-3 mt-1 text-gray-500">
                          <span>score: {d.score.toFixed(2)}</span>
                          <span>conf: {d.confidence.toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tags */}
                {f.attempt.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {f.attempt.tags.map((tag) => (
                      <span key={tag} className="badge badge-info">{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-400">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
