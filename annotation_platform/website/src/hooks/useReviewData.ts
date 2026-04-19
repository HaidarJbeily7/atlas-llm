import { useEffect, useState, useCallback } from 'react';
import {
  listReviews,
  annotationCounts,
  type ReviewAggregate,
  type Settlement,
} from '../lib/annotations';
import type { FindingIndex } from '../types';

export interface ReviewStats {
  total: number;
  needsReview: number;
  reviewed: number;
  confirmed: number;
  falsePositive: number;
  investigating: number;
  wontFix: number;
  disputed: number;
  reviewedPassRate: number | null;
  reviewedFailCount: number;
  reviewedPassCount: number;
}

interface ReviewData {
  reviewMap: Record<string, ReviewAggregate>;
  annMap: Record<string, number>;
  backendOk: boolean | null;
  refresh: () => Promise<void>;
  getSettlement: (findingId: string) => Settlement;
  computeReviewStats: (findings: FindingIndex[]) => ReviewStats;
}

export function useReviewData(): ReviewData {
  const [reviewMap, setReviewMap] = useState<Record<string, ReviewAggregate>>({});
  const [annMap, setAnnMap] = useState<Record<string, number>>({});
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [reviews, counts] = await Promise.all([listReviews(), annotationCounts()]);
      const m: Record<string, ReviewAggregate> = {};
      for (const r of reviews) m[r.finding_id] = r;
      setReviewMap(m);
      setAnnMap(counts);
      setBackendOk(true);
    } catch {
      setBackendOk(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const getSettlement = useCallback(
    (findingId: string): Settlement => reviewMap[findingId]?.settlement ?? 'open',
    [reviewMap],
  );

  const computeReviewStats = useCallback(
    (findings: FindingIndex[]): ReviewStats => {
      let needsReview = 0;
      let reviewed = 0;
      let confirmed = 0;
      let falsePositive = 0;
      let investigating = 0;
      let wontFix = 0;
      let disputed = 0;
      let reviewedPass = 0;
      let reviewedFail = 0;

      for (const f of findings) {
        const rev = reviewMap[f.id];
        const settlement: Settlement = rev?.settlement ?? 'open';

        if (settlement === 'open') {
          needsReview++;
        } else {
          reviewed++;
          if (settlement === 'disputed') {
            disputed++;
          } else {
            // partial or settled — count pass/fail from the reviewed data
            if (rev?.status === 'confirmed_vulnerability') confirmed++;
            else if (rev?.status === 'false_positive') falsePositive++;
            else if (rev?.status === 'needs_investigation') investigating++;
            else if (rev?.status === 'wont_fix') wontFix++;
          }

          // For reviewed stats, use the finding's pass/fail
          if (f.passed) reviewedPass++;
          else reviewedFail++;
        }
      }

      const reviewedTotal = reviewedPass + reviewedFail;
      return {
        total: findings.length,
        needsReview,
        reviewed,
        confirmed,
        falsePositive,
        investigating,
        wontFix,
        disputed,
        reviewedPassRate: reviewedTotal > 0 ? (reviewedPass / reviewedTotal) * 100 : null,
        reviewedFailCount: reviewedFail,
        reviewedPassCount: reviewedPass,
      };
    },
    [reviewMap],
  );

  return { reviewMap, annMap, backendOk, refresh, getSettlement, computeReviewStats };
}
