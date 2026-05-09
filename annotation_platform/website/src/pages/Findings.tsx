import { useState, useMemo, useCallback } from 'react';
import { useExperimentData } from '../hooks/useExperimentData';
import { useReviewData } from '../hooks/useReviewData';
import LoadingSpinner from '../components/LoadingSpinner';
import AnnotationPanel from '../components/AnnotationPanel';
import { getProbeLabel, shortModelName, formatCost, loadFindingDetail } from '../lib/data';
import {
  reviewStatusColor,
  reviewStatusLabel,
  settlementColor,
  settlementLabel,
  type ReviewStatus,
  type Settlement,
} from '../lib/annotations';
import type { FindingIndex, FindingDetail } from '../types';
import clsx from 'clsx';

function DetectorCard({ d }: { d: FindingDetail['detector_results'][number] }) {
  const [open, setOpen] = useState(false);
  const hasDimensions = d.dimension_scores && Object.keys(d.dimension_scores).length > 0;
  const hasPatterns = d.matched_patterns && d.matched_patterns.length > 0;

  return (
    <div className={clsx('rounded-lg text-xs border transition-colors',
      d.passed ? 'bg-green-900/20 border-green-800/50' : 'bg-red-900/20 border-red-800/50')}>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className="w-full text-left px-3 py-2 cursor-pointer"
      >
        <div className="flex justify-between items-center mb-1">
          <span className="font-medium text-gray-200">{d.detector_name}</span>
          <span className="flex items-center gap-1.5">
            {d.needs_human_review && (
              <span className="text-amber-400" title="Needs human review">⚠</span>
            )}
            <span className={d.passed ? 'text-green-400' : 'text-red-400'}>{d.passed ? 'PASS' : 'FAIL'}</span>
            <svg className={clsx('w-3 h-3 text-gray-500 transition-transform', open && 'rotate-180')}
              fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </span>
        </div>
        <p className={clsx('text-gray-400', !open && 'truncate')}>{d.evidence}</p>
        <div className="flex gap-3 mt-1 text-gray-500">
          <span>score: {d.score.toFixed(2)}</span>
          <span>conf: {d.confidence.toFixed(2)}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-gray-700/50 px-3 py-2 space-y-2 text-xs">
          {/* Full evidence (always shown when expanded) */}
          <div>
            <p className="text-gray-500 mb-1">Evidence:</p>
            <pre className="text-gray-300 bg-gray-800/60 rounded px-2 py-1.5 whitespace-pre-wrap max-h-48 overflow-auto">
              {d.evidence || '(none)'}
            </pre>
          </div>

          {/* Key details grid — always visible */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-400">
            <span>Score: <span className="text-white">{d.score.toFixed(3)}</span></span>
            <span>Confidence: <span className="text-white">{d.confidence.toFixed(3)}</span></span>
            <span>Status: <span className={d.passed ? 'text-green-400' : 'text-red-400'}>{d.passed ? 'PASS' : 'FAIL'}</span></span>
            <span>Needs Human Review: <span className={d.needs_human_review ? 'text-amber-400' : 'text-gray-500'}>{d.needs_human_review ? 'Yes' : 'No'}</span></span>
            <span>Failure Type: <span className="text-white">{d.failure_type || '-'}</span></span>
          </div>

          {/* Judge reasoning */}
          <div>
            <p className="text-gray-500 mb-1">Judge Reasoning:</p>
            <pre className="text-gray-300 bg-gray-800/60 rounded px-2 py-1.5 whitespace-pre-wrap max-h-48 overflow-auto">
              {d.judge_reasoning || '(no reasoning available)'}
            </pre>
          </div>

          {/* Judge metadata */}
          <div className="flex flex-wrap gap-3 text-gray-400">
            <span>Judge Model: <span className="text-gray-200">{d.judge_model || '-'}</span></span>
            {d.judge_model && (
              <>
                <span>Tokens: <span className="text-gray-200">{d.judge_tokens_in} in / {d.judge_tokens_out} out</span></span>
                <span>Cost: <span className="text-gray-200">{formatCost(d.judge_cost_usd ?? 0)}</span></span>
                <span>Latency: <span className="text-gray-200">{((d.judge_latency_ms ?? 0) / 1000).toFixed(1)}s</span></span>
              </>
            )}
          </div>

          {/* Dimension scores */}
          {hasDimensions && (
            <div>
              <p className="text-gray-500 mb-1">Dimension Scores:</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(d.dimension_scores).map(([dim, val]) => (
                  <span key={dim} className="bg-gray-800/60 rounded px-2 py-0.5 text-gray-300">
                    {dim}: <span className="text-white font-medium">{val}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Matched patterns */}
          {hasPatterns && (
            <div>
              <p className="text-gray-500 mb-1">Matched Patterns:</p>
              <div className="flex flex-wrap gap-1">
                {d.matched_patterns.map((p, i) => (
                  <span key={i} className="bg-gray-800/60 rounded px-2 py-0.5 text-amber-300">{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

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
            {formatCost(a.cost_usd - (isAdaptive ? a.cost_usd * a.attacker_tokens_in / Math.max(1, a.attacker_tokens_in + a.target_tokens_in) : 0))}
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">{a.target_tokens_in} in / {a.target_tokens_out} out</p>
        </div>
        <div className={clsx('rounded-lg p-3', isAdaptive ? 'bg-purple-900/20 border border-purple-800/30' : 'bg-gray-800/50')}>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Attacker Cost</p>
          <p className="text-sm font-semibold text-purple-300">
            {isAdaptive ? formatCost(a.cost_usd * a.attacker_tokens_in / Math.max(1, a.attacker_tokens_in + a.target_tokens_in)) : '-'}
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">
            {a.attacker_tokens_in > 0 ? `${a.attacker_tokens_in} in / ${a.attacker_tokens_out} out` : 'No attacker model'}
          </p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Total Cost</p>
          <p className="text-sm font-semibold text-white">{formatCost(a.cost_usd)}</p>
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
        <div className={clsx('flex gap-4 text-xs rounded-lg px-4 py-2', {
          'bg-blue-900/10 border border-blue-800/20': meta.condition === 'adaptive_single_query_st',
          'bg-amber-900/10 border border-amber-800/20': meta.condition === 'adaptive_single_turn',
          'bg-purple-900/10 border border-purple-800/20': meta.condition === 'adaptive_multi_turn',
        })}>
          <span className="text-gray-500">Strategy: <span className="text-white font-medium">
            {meta.condition === 'adaptive_single_query_st' ? 'PAIR Single-Query (1 iter)' :
             meta.condition === 'adaptive_single_turn' ? 'PAIR Multi-Query (up to 5 iter)' :
             meta.condition === 'adaptive_multi_turn' ? 'LLM-driven Multi-Turn' : String(meta.condition ?? '-')}
          </span></span>
          <span className="text-gray-500">PAIR Score: <span className="text-purple-300 font-medium">{String(meta.pair_score ?? '-')}</span></span>
          <span className="text-gray-500">Iteration: <span className="text-purple-300 font-medium">{String(meta.pair_iteration ?? meta.turns_completed ?? '-')}</span></span>
          <span className="text-gray-500">Attack Successful: <span className={clsx('font-medium', meta.attack_successful || meta.pair_successful ? 'text-red-400' : 'text-green-400')}>{String(meta.attack_successful ?? meta.pair_successful ?? '-')}</span></span>
          <span className="text-gray-500">Best Score: <span className="text-purple-300 font-medium">{String(meta.best_score ?? '-')}</span></span>
        </div>
      )}

      {/* Detector results */}
      <div>
        <p className="text-xs text-gray-500 mb-2 font-medium">Detector Results</p>
        <div className="grid grid-cols-3 gap-2">
          {finding.detector_results.map((d, i) => (
            <DetectorCard key={i} d={d} />
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
  const { reviewMap, annMap, reviewStats, backendOk, refresh: refreshReviews } = useReviewData();
  const [filterPassed, setFilterPassed] = useState<'all' | 'passed' | 'failed'>('all');
  const [filterModel, setFilterModel] = useState<string>('all');
  const [filterProbe, setFilterProbe] = useState<string>('all');
  const [filterReview, setFilterReview] = useState<'all' | 'needs_review' | Settlement | ReviewStatus>('all');
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
      if (filterReview !== 'all') {
        const rev = reviewMap[f.id];
        const settlement: Settlement = rev?.settlement ?? 'open';
        const status = rev?.status ?? null;
        if (filterReview === 'needs_review') {
          if (settlement !== 'open') return false;
        } else if (filterReview === 'open' || filterReview === 'partial'
            || filterReview === 'settled' || filterReview === 'disputed') {
          if (settlement !== filterReview) return false;
        } else if (status !== filterReview) {
          return false;
        }
      }
      return true;
    });
  }, [findings, filterPassed, filterModel, filterProbe, filterReview, reviewMap]);

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

  const reviewPct = reviewStats && reviewStats.total > 0
    ? (reviewStats.reviewed / reviewStats.total) * 100
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Findings Explorer</h1>
        <p className="text-gray-500 mt-1">
          {findings.length} total findings across all scans
          {backendOk === false ? (
            <span className="ml-2 text-amber-400 text-xs">
              (annotation backend unreachable — investigation features disabled)
            </span>
          ) : null}
        </p>
      </div>

      {/* Review progress bar */}
      {backendOk && reviewStats && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Review Progress</h2>
            <span className="text-xs text-gray-400">
              {reviewStats.reviewed} / {reviewStats.total} reviewed ({reviewPct.toFixed(0)}%)
            </span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
            <div
              className="h-full rounded-full transition-all bg-indigo-500"
              style={{ width: `${reviewPct}%` }}
            />
          </div>
          <div className="flex flex-wrap gap-3 text-xs">
            <button
              onClick={() => { setFilterReview('needs_review'); setPage(0); }}
              className={clsx(
                'rounded px-2 py-1 transition-colors',
                filterReview === 'needs_review'
                  ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50'
                  : 'bg-amber-900/20 text-amber-400 border border-amber-800/30 hover:bg-amber-900/30',
              )}
            >
              Needs Review: {reviewStats.needs_review}
            </button>
            <button
              onClick={() => { setFilterReview('confirmed_vulnerability'); setPage(0); }}
              className={clsx(
                'rounded px-2 py-1 transition-colors',
                filterReview === 'confirmed_vulnerability'
                  ? 'bg-red-500/30 text-red-300 border border-red-500/50'
                  : 'bg-red-900/20 text-red-400 border border-red-800/30 hover:bg-red-900/30',
              )}
            >
              Confirmed: {reviewStats.confirmed}
            </button>
            <button
              onClick={() => { setFilterReview('false_positive'); setPage(0); }}
              className={clsx(
                'rounded px-2 py-1 transition-colors',
                filterReview === 'false_positive'
                  ? 'bg-green-500/30 text-green-300 border border-green-500/50'
                  : 'bg-green-900/20 text-green-400 border border-green-800/30 hover:bg-green-900/30',
              )}
            >
              False Positive: {reviewStats.false_positive}
            </button>
            <button
              onClick={() => { setFilterReview('false_negative'); setPage(0); }}
              className={clsx(
                'rounded px-2 py-1 transition-colors',
                filterReview === 'false_negative'
                  ? 'bg-purple-500/30 text-purple-300 border border-purple-500/50'
                  : 'bg-purple-900/20 text-purple-400 border border-purple-800/30 hover:bg-purple-900/30',
              )}
              title="Judges said PASS but attack actually succeeded — judges missed it"
            >
              False Negative: {reviewStats.false_negative}
            </button>
            <button
              onClick={() => { setFilterReview('needs_investigation'); setPage(0); }}
              className={clsx(
                'rounded px-2 py-1 transition-colors',
                filterReview === 'needs_investigation'
                  ? 'bg-amber-500/30 text-amber-200 border border-amber-500/50'
                  : 'bg-gray-800 text-amber-300 border border-gray-700 hover:bg-gray-700',
              )}
            >
              Investigating: {reviewStats.investigating}
            </button>
            <button
              onClick={() => { setFilterReview('disputed'); setPage(0); }}
              className={clsx(
                'rounded px-2 py-1 transition-colors',
                filterReview === 'disputed'
                  ? 'bg-orange-500/30 text-orange-300 border border-orange-500/50'
                  : 'bg-orange-900/20 text-orange-400 border border-orange-800/30 hover:bg-orange-900/30',
              )}
            >
              Disputed: {reviewStats.disputed}
            </button>
            {filterReview !== 'all' && (
              <button
                onClick={() => { setFilterReview('all'); setPage(0); }}
                className="rounded px-2 py-1 bg-gray-800 text-gray-400 border border-gray-700 hover:bg-gray-700"
              >
                Clear filter
              </button>
            )}
          </div>
          {reviewStats.reviewed > 0 && (
            <div className="flex gap-4 text-xs text-gray-500 border-t border-gray-800 pt-2">
              <span>Reviewed stats:</span>
              <span>Pass rate: <span className="text-white font-medium">{reviewStats.reviewed_pass_rate?.toFixed(1)}%</span></span>
              <span>Passed: <span className="text-green-400 font-medium">{reviewStats.reviewed_pass_count}</span></span>
              <span>Failed: <span className="text-red-400 font-medium">{reviewStats.reviewed_fail_count}</span></span>
            </div>
          )}
        </div>
      )}

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
        <div>
          <label className="text-xs text-gray-500 block mb-1">Review</label>
          <select value={filterReview}
            onChange={(e) => { setFilterReview(e.target.value as 'all' | 'needs_review' | Settlement | ReviewStatus); setPage(0); }}
            disabled={!backendOk}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 disabled:opacity-40">
            <option value="all">All</option>
            <option value="needs_review">Needs Review</option>
            <optgroup label="Settlement">
              <option value="open">Open (no votes)</option>
              <option value="partial">Partial (1 voter)</option>
              <option value="settled">Settled</option>
              <option value="disputed">Disputed</option>
            </optgroup>
            <optgroup label="Settled status">
              <option value="confirmed_vulnerability">Confirmed Vuln (judges + human agree — attack succeeded)</option>
              <option value="confirmed_safe">Confirmed Safe (judges + human agree — model refused)</option>
              <option value="false_positive">False Positive (judges wrong — model was safe)</option>
              <option value="false_negative">False Negative (judges wrong — attack succeeded)</option>
              <option value="needs_investigation">Investigating</option>
              <option value="wont_fix">Won't Fix</option>
            </optgroup>
          </select>
        </div>
        <div className="ml-auto text-sm text-gray-400">
          Showing {filtered.length} findings
        </div>
      </div>

      {/* Findings list */}
      <div className="space-y-2">
        {paged.map((f) => {
          const rev = reviewMap[f.id];
          const settlement: Settlement = rev?.settlement ?? 'open';
          const settledStatus = rev?.status ?? null;
          const annCount = annMap[f.id] ?? 0;
          return (
            <div key={f.id} className="card !p-0 overflow-hidden">
              <button
                onClick={() => handleExpand(f)}
                className="w-full text-left px-4 py-3 flex items-center gap-2 hover:bg-gray-800/50 transition-colors min-w-0 overflow-hidden"
              >
                <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', f.passed ? 'bg-green-500' : 'bg-red-500')} />
                <span className="text-sm font-medium text-white flex-1 min-w-0 truncate">
                  {f.prompt_preview}...
                </span>
                <span className="flex items-center gap-1.5 flex-shrink-0 flex-wrap justify-end">
                  {annCount > 0 && (
                    <span className="text-[10px] text-indigo-300 bg-indigo-900/30 border border-indigo-800/40 rounded px-1.5 py-0.5 whitespace-nowrap">
                      {annCount} note{annCount === 1 ? '' : 's'}
                    </span>
                  )}
                  {backendOk && settlement === 'open' && (
                    <span className="text-[10px] font-medium rounded px-1.5 py-0.5 bg-amber-900/40 text-amber-300 border border-amber-700/50 animate-pulse whitespace-nowrap">
                      Review
                    </span>
                  )}
                  {backendOk && settlement !== 'open' && (
                    <span className={clsx('text-[10px] font-medium rounded px-1.5 py-0.5 whitespace-nowrap', settlementColor(settlement))}>
                      {settlementLabel(settlement)}
                      {rev && rev.distinct_voter_count > 1 ? ` · ${rev.distinct_voter_count}` : ''}
                    </span>
                  )}
                  {backendOk && settlement === 'settled' && settledStatus && (
                    <span className={clsx('text-[10px] font-medium rounded px-1.5 py-0.5 whitespace-nowrap', reviewStatusColor(settledStatus))}>
                      {reviewStatusLabel(settledStatus)}
                    </span>
                  )}
                  {f.num_messages > 0 && (
                    <span className="badge badge-warning text-[10px] whitespace-nowrap">{Math.ceil(f.num_messages / 2)}T</span>
                  )}
                  {f.condition && (
                    <span className={clsx('text-[10px] font-medium whitespace-nowrap', {
                      'text-gray-500': !f.condition || f.condition === 'jailbreak' || f.condition === 'static_multi_turn',
                      'text-blue-400': f.condition === 'adaptive_single_query_st',
                      'text-amber-400': f.condition === 'adaptive_single_turn',
                      'text-purple-400': f.condition === 'adaptive_multi_turn',
                    })}>
                      {f.condition === 'adaptive_single_query_st' ? '1Q' :
                       f.condition === 'adaptive_single_turn' ? 'MQ' :
                       f.condition === 'adaptive_multi_turn' ? 'MT' : null}
                    </span>
                  )}
                  <span className="badge badge-info text-[10px] whitespace-nowrap">{f.model_short}</span>
                  <span className="text-[10px] text-gray-500 whitespace-nowrap">{getProbeLabel(f.probe)}</span>
                  <span className={clsx('badge whitespace-nowrap', f.passed ? 'badge-success' : 'badge-danger')}>
                    {f.passed ? 'PASS' : 'FAIL'}
                  </span>
                </span>
              </button>

              {expandedId === f.id && (
                detailLoading ? (
                  <div className="border-t border-gray-800 px-4 py-6">
                    <LoadingSpinner />
                  </div>
                ) : expandedDetail ? (
                  <>
                    <FindingExpanded finding={expandedDetail} />
                    {backendOk ? (
                      <AnnotationPanel
                        key={f.id}
                        findingId={f.id}
                        onReviewChange={() => { void refreshReviews(); }}
                        onAnnotationsChange={() => { void refreshReviews(); }}
                      />
                    ) : null}
                  </>
                ) : (
                  <div className="border-t border-gray-800 px-4 py-4 text-sm text-red-400">
                    Failed to load finding details
                  </div>
                )
              )}
            </div>
          );
        })}
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
