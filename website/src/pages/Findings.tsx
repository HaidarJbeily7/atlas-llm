import { useState, useMemo, useCallback } from 'react';
import { useExperimentData } from '../hooks/useExperimentData';
import LoadingSpinner from '../components/LoadingSpinner';
import { getProbeLabel, shortModelName, loadFindingDetail } from '../lib/data';
import type { FindingIndex, FindingDetail } from '../types';
import clsx from 'clsx';

function FindingExpanded({ finding }: { finding: FindingDetail }) {
  const a = finding.attempt;
  const meta = a.metadata;
  const isMultiTurn = a.messages.length > 0;
  const isAdaptive = a.num_attacker_calls > 0;

  return (
    <div className="border-t border-gray-800 px-4 py-4 space-y-4">
      {/* Metadata row */}
      <div className="flex flex-wrap gap-3 text-xs">
        <span className={clsx('badge', {
          'badge-danger': finding.severity === 'critical',
          'badge-warning': finding.severity === 'high' || finding.severity === 'medium',
          'badge-success': finding.severity === 'low',
        })}>{finding.severity} severity</span>
        {meta.condition ? <span className="badge badge-info">{String(meta.condition)}</span> : null}
        {meta.objective ? (
          <span className="text-gray-400 italic">
            Objective: {String(meta.objective).slice(0, 120)}
          </span>
        ) : null}
      </div>

      {/* Cost breakdown */}
      <div className="grid grid-cols-6 gap-3">
        <div className="bg-gray-800/50 rounded-lg p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Target Cost</p>
          <p className="text-sm font-semibold text-white">
            ${(a.cost_usd - (isAdaptive ? a.cost_usd * a.attacker_tokens_in / Math.max(1, a.attacker_tokens_in + a.target_tokens_in) : 0)).toFixed(4)}
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">{a.target_tokens_in} in / {a.target_tokens_out} out</p>
        </div>
        <div className={clsx('rounded-lg p-3', isAdaptive ? 'bg-purple-900/20 border border-purple-800/30' : 'bg-gray-800/50')}>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Attacker Cost</p>
          <p className="text-sm font-semibold text-purple-300">
            {isAdaptive ? `$${(a.cost_usd * a.attacker_tokens_in / Math.max(1, a.attacker_tokens_in + a.target_tokens_in)).toFixed(4)}` : '-'}
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">
            {a.attacker_tokens_in > 0 ? `${a.attacker_tokens_in} in / ${a.attacker_tokens_out} out` : 'No attacker model'}
          </p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Total Cost</p>
          <p className="text-sm font-semibold text-white">${a.cost_usd.toFixed(4)}</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Latency</p>
          <p className="text-sm font-semibold text-white">{(a.latency_ms / 1000).toFixed(1)}s</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Target Calls</p>
          <p className="text-sm font-semibold text-white">{a.num_target_calls}</p>
        </div>
        <div className={clsx('rounded-lg p-3', isAdaptive ? 'bg-purple-900/20 border border-purple-800/30' : 'bg-gray-800/50')}>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Attacker Calls</p>
          <p className="text-sm font-semibold text-purple-300">{a.num_attacker_calls || '-'}</p>
        </div>
      </div>

      {/* Conversation thread or prompt/response */}
      {isMultiTurn ? (
        <div>
          <p className="text-xs text-gray-500 mb-2 font-medium">
            Conversation ({a.messages.length} messages, {Math.ceil(a.messages.length / 2)} turns)
          </p>
          <div className="bg-gray-800/40 rounded-lg p-4 max-h-96 overflow-auto space-y-3">
            {a.messages.map((msg, i) => (
              <div key={i} className={clsx('flex gap-3', msg.role === 'assistant' ? 'justify-start' : 'justify-end')}>
                <div className={clsx(
                  'max-w-[80%] rounded-lg px-3 py-2 text-xs',
                  msg.role === 'assistant'
                    ? 'bg-gray-700/60 text-gray-200'
                    : 'bg-indigo-900/40 border border-indigo-800/30 text-indigo-100'
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={clsx('text-[10px] font-semibold uppercase tracking-wider',
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
            <pre className="text-xs text-gray-300 bg-gray-800 rounded-lg p-3 max-h-48 overflow-auto whitespace-pre-wrap">{a.prompt}</pre>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1 font-medium">Response</p>
            <pre className="text-xs text-gray-300 bg-gray-800 rounded-lg p-3 max-h-48 overflow-auto whitespace-pre-wrap">{a.response}</pre>
          </div>
        </div>
      )}

      {/* Adaptive metadata */}
      {meta.adaptivity === 'adaptive' && (
        <div className="flex gap-4 text-xs bg-purple-900/10 border border-purple-800/20 rounded-lg px-4 py-2">
          <span className="text-gray-500">PAIR Score: <span className="text-purple-300 font-medium">{String(meta.pair_score ?? '-')}</span></span>
          <span className="text-gray-500">Attack Successful: <span className={clsx('font-medium', meta.attack_successful ? 'text-red-400' : 'text-green-400')}>{String(meta.attack_successful ?? '-')}</span></span>
          <span className="text-gray-500">Turns: <span className="text-purple-300 font-medium">{String(meta.turns_completed ?? '-')}</span></span>
          <span className="text-gray-500">Best Score: <span className="text-purple-300 font-medium">{String(meta.best_score ?? '-')}</span></span>
        </div>
      )}

      {/* Detector results */}
      <div>
        <p className="text-xs text-gray-500 mb-2 font-medium">Detector Results</p>
        <div className="grid grid-cols-3 gap-2">
          {finding.detector_results.map((d, i) => (
            <div key={i} className={clsx('rounded-lg px-3 py-2 text-xs border',
              d.passed ? 'bg-green-900/20 border-green-800/50' : 'bg-red-900/20 border-red-800/50')}>
              <div className="flex justify-between items-center mb-1">
                <span className="font-medium text-gray-200">{d.detector_name}</span>
                <span className={d.passed ? 'text-green-400' : 'text-red-400'}>{d.passed ? 'PASS' : 'FAIL'}</span>
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
      {a.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {a.tags.map((tag) => <span key={tag} className="badge badge-info">{tag}</span>)}
        </div>
      )}
    </div>
  );
}

export default function Findings() {
  const { summary, loading } = useExperimentData();
  const [filterPassed, setFilterPassed] = useState<'all' | 'passed' | 'failed'>('all');
  const [filterModel, setFilterModel] = useState<string>('all');
  const [filterProbe, setFilterProbe] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<FindingDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [page, setPage] = useState(0);

  const PAGE_SIZE = 20;

  const findings = summary?.findings_index ?? [];
  const modelNames = useMemo(() => [...new Set(findings.map((f) => f.model))], [findings]);
  const probeNames = useMemo(() => [...new Set(findings.map((f) => f.probe))], [findings]);

  const filtered = useMemo(() => {
    return findings.filter((f) => {
      if (filterPassed === 'passed' && !f.passed) return false;
      if (filterPassed === 'failed' && f.passed) return false;
      if (filterModel !== 'all' && f.model !== filterModel) return false;
      if (filterProbe !== 'all' && f.probe !== filterProbe) return false;
      return true;
    });
  }, [findings, filterPassed, filterModel, filterProbe]);

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  const handleExpand = useCallback(async (f: FindingIndex) => {
    if (expandedId === f.id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(f.id);
    setDetailLoading(true);
    try {
      const detail = await loadFindingDetail(f.id);
      setExpandedDetail(detail);
    } catch {
      setExpandedDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, [expandedId]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Findings Explorer</h1>
        <p className="text-gray-500 mt-1">{findings.length} total findings across all scans</p>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-4 items-center">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Status</label>
          <select value={filterPassed}
            onChange={(e) => { setFilterPassed(e.target.value as 'all' | 'passed' | 'failed'); setPage(0); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200">
            <option value="all">All</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Model</label>
          <select value={filterModel}
            onChange={(e) => { setFilterModel(e.target.value); setPage(0); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200">
            <option value="all">All Models</option>
            {modelNames.map((m) => <option key={m} value={m}>{shortModelName(m)}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Probe</label>
          <select value={filterProbe}
            onChange={(e) => { setFilterProbe(e.target.value); setPage(0); }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200">
            <option value="all">All Probes</option>
            {probeNames.map((p) => <option key={p} value={p}>{getProbeLabel(p)}</option>)}
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
              onClick={() => handleExpand(f)}
              className="w-full text-left px-4 py-3 flex items-center gap-4 hover:bg-gray-800/50 transition-colors"
            >
              <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', f.passed ? 'bg-green-500' : 'bg-red-500')} />
              <span className="text-sm font-medium text-white flex-1 truncate">
                {f.prompt_preview}...
              </span>
              {f.num_messages > 0 && (
                <span className="badge badge-warning text-[10px]">{Math.ceil(f.num_messages / 2)} turns</span>
              )}
              {f.num_attacker_calls > 0 && (
                <span className="text-[10px] text-purple-400 font-medium">ADAPTIVE</span>
              )}
              <span className="badge badge-info text-xs">{f.model_short}</span>
              <span className="text-xs text-gray-500">{getProbeLabel(f.probe)}</span>
              <span className={clsx('badge', f.passed ? 'badge-success' : 'badge-danger')}>
                {f.passed ? 'PASS' : 'FAIL'}
              </span>
            </button>

            {expandedId === f.id && (
              detailLoading ? (
                <div className="border-t border-gray-800 px-4 py-6">
                  <LoadingSpinner />
                </div>
              ) : expandedDetail ? (
                <FindingExpanded finding={expandedDetail} />
              ) : (
                <div className="border-t border-gray-800 px-4 py-4 text-sm text-red-400">
                  Failed to load finding details
                </div>
              )
            )}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700">
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-400">Page {page + 1} of {totalPages}</span>
          <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 disabled:opacity-40 hover:bg-gray-700">
            Next
          </button>
        </div>
      )}
    </div>
  );
}
