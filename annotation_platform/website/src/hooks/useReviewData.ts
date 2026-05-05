import { useEffect, useState, useCallback } from 'react';
import {
  listReviews,
  annotationCounts,
  fetchReviewStats,
  type ReviewAggregate,
  type ReviewStats,
} from '../lib/annotations';
import { getActiveExperiment } from '../lib/data';

export type { ReviewStats } from '../lib/annotations';

interface ReviewData {
  reviewMap: Record<string, ReviewAggregate>;
  annMap: Record<string, number>;
  reviewStats: ReviewStats | null;
  backendOk: boolean | null;
  refresh: () => Promise<void>;
}

const EMPTY_STATS: ReviewStats = {
  total: 0,
  needs_review: 0,
  reviewed: 0,
  confirmed: 0,
  false_positive: 0,
  false_negative: 0,
  investigating: 0,
  wont_fix: 0,
  disputed: 0,
  reviewed_pass_rate: null,
  reviewed_fail_count: 0,
  reviewed_pass_count: 0,
};

export function useReviewData(): ReviewData {
  const [reviewMap, setReviewMap] = useState<Record<string, ReviewAggregate>>({});
  const [annMap, setAnnMap] = useState<Record<string, number>>({});
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const expId = getActiveExperiment() ?? undefined;
      const [reviews, counts, stats] = await Promise.all([
        listReviews(),
        annotationCounts(),
        fetchReviewStats(expId),
      ]);
      const m: Record<string, ReviewAggregate> = {};
      for (const r of reviews) m[r.finding_id] = r;
      setReviewMap(m);
      setAnnMap(counts);
      setReviewStats(stats);
      setBackendOk(true);
    } catch {
      setBackendOk(false);
      setReviewStats(EMPTY_STATS);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { reviewMap, annMap, reviewStats, backendOk, refresh };
}
