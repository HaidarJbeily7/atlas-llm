// Client for the investigation/annotation/review API.
//
// Writes require a bearer token (see lib/auth.ts). Reads are public.

import { authedFetch } from './auth';

export const REVIEW_STATUSES = [
  'pending',
  'confirmed_vulnerability',
  'false_positive',
  'false_negative',
  'needs_investigation',
  'wont_fix',
] as const;

export type ReviewStatus = typeof REVIEW_STATUSES[number];

export type Settlement = 'open' | 'partial' | 'settled' | 'disputed';

export interface Annotation {
  id: number;
  finding_id: string;
  label: string;
  note: string;
  author: string;
  created_at: string;
  updated_at: string;
}

export interface Vote {
  id: number;
  finding_id: string;
  user_id: number;
  username: string;
  status: ReviewStatus;
  rationale: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewSummary {
  finding_id: string;
  settlement: Settlement;
  status: ReviewStatus | null;
  vote_count: number;
  distinct_voter_count: number;
  votes: Vote[];
  my_vote: Vote | null;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authedFetch(path, init);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---- annotations ---------------------------------------------------------

export function listAnnotations(findingId: string): Promise<Annotation[]> {
  return req(`/api/findings/${encodeURIComponent(findingId)}/annotations`);
}

export function createAnnotation(
  findingId: string,
  body: { label?: string; note?: string }
): Promise<Annotation> {
  return req(`/api/findings/${encodeURIComponent(findingId)}/annotations`, {
    method: 'POST',
    body: JSON.stringify({ label: '', note: '', ...body }),
  });
}

export function updateAnnotation(
  id: number,
  patch: { label?: string; note?: string }
): Promise<Annotation> {
  return req(`/api/annotations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export function deleteAnnotation(id: number): Promise<void> {
  return req(`/api/annotations/${id}`, { method: 'DELETE' });
}

export function annotationCounts(): Promise<Record<string, number>> {
  return req('/api/annotations/counts');
}

// ---- reviews / voting ---------------------------------------------------

export function getReview(findingId: string): Promise<ReviewSummary> {
  return req(`/api/findings/${encodeURIComponent(findingId)}/review`);
}

export function castVote(
  findingId: string,
  body: { status: ReviewStatus; rationale?: string }
): Promise<ReviewSummary> {
  return req(`/api/findings/${encodeURIComponent(findingId)}/review`, {
    method: 'PUT',
    body: JSON.stringify({ rationale: '', ...body }),
  });
}

export function withdrawVote(findingId: string): Promise<ReviewSummary> {
  return req(`/api/findings/${encodeURIComponent(findingId)}/review`, {
    method: 'DELETE',
  });
}

// Aggregate of every finding that has at least one vote (for list badges).
export interface ReviewAggregate {
  finding_id: string;
  settlement: Settlement;
  status: ReviewStatus | null;
  vote_count: number;
  distinct_voter_count: number;
}

export function listReviews(): Promise<ReviewAggregate[]> {
  return req('/api/reviews');
}

// ---- review stats (backend-computed) ------------------------------------

export interface ReviewStats {
  total: number;
  needs_review: number;
  reviewed: number;
  confirmed: number;
  false_positive: number;
  false_negative: number;
  investigating: number;
  wont_fix: number;
  disputed: number;
  reviewed_pass_rate: number | null;
  reviewed_fail_count: number;
  reviewed_pass_count: number;
}

export function fetchReviewStats(experimentId?: string): Promise<ReviewStats> {
  const path = experimentId
    ? `/api/experiments/${encodeURIComponent(experimentId)}/review-stats`
    : '/api/review-stats';
  return req(path);
}

// ---- labels / colors ----------------------------------------------------

export function reviewStatusLabel(s: ReviewStatus): string {
  const labels: Record<ReviewStatus, string> = {
    pending: 'Pending',
    confirmed_vulnerability: 'Confirmed',
    false_positive: 'False Positive',
    false_negative: 'False Negative',
    needs_investigation: 'Investigating',
    wont_fix: "Won't Fix",
  };
  return labels[s];
}

export function reviewStatusColor(s: ReviewStatus): string {
  const colors: Record<ReviewStatus, string> = {
    pending: 'bg-gray-700 text-gray-300',
    confirmed_vulnerability: 'bg-red-900/40 text-red-300 border border-red-800/50',
    false_positive: 'bg-green-900/40 text-green-300 border border-green-800/50',
    false_negative: 'bg-purple-900/40 text-purple-300 border border-purple-800/50',
    needs_investigation: 'bg-amber-900/40 text-amber-300 border border-amber-800/50',
    wont_fix: 'bg-gray-800 text-gray-400 border border-gray-700',
  };
  return colors[s];
}

/** Definitions for each review status — used in tooltips. */
export function reviewStatusDefinition(s: ReviewStatus): string {
  const defs: Record<ReviewStatus, string> = {
    pending: 'Not yet reviewed by a human annotator.',
    confirmed_vulnerability: 'Judges said FAIL and human agrees — the attack succeeded.',
    false_positive: 'Judges said FAIL but human disagrees — the model actually refused or the response is safe. The judges were wrong.',
    false_negative: 'Judges said PASS but human disagrees — the attack actually succeeded but judges missed it. The judges were wrong.',
    needs_investigation: 'Unclear — needs deeper analysis before a verdict.',
    wont_fix: 'Real issue but out of scope or accepted risk.',
  };
  return defs[s];
}

export function settlementLabel(s: Settlement): string {
  return { open: 'Open', partial: '1 vote', settled: 'Settled', disputed: 'Disputed' }[s];
}

export function settlementColor(s: Settlement): string {
  return {
    open: 'bg-gray-800 text-gray-500 border border-gray-700',
    partial: 'bg-indigo-900/30 text-indigo-300 border border-indigo-800/40',
    settled: 'bg-green-900/40 text-green-300 border border-green-800/50',
    disputed: 'bg-amber-900/40 text-amber-300 border border-amber-800/50',
  }[s];
}

/** Check whether the backend is reachable. Returns false on any network/HTTP error. */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_BASE ?? ''}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
