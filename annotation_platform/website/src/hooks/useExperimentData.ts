import { useEffect, useState } from 'react';
import type { Summary, ModelAggregation } from '../types';
import { loadSummary, aggregateByModel, subscribeActiveExperiment } from '../lib/data';

interface ExperimentData {
  summary: Summary | null;
  models: ModelAggregation[];
  loading: boolean;
  error: string | null;
}

export function useExperimentData(): ExperimentData {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [models, setModels] = useState<ModelAggregation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => subscribeActiveExperiment(() => setVersion((v) => v + 1)), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loadSummary()
      .then((data) => {
        if (cancelled) return;
        setSummary(data);
        setModels(aggregateByModel(data.scans));
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [version]);

  return { summary, models, loading, error };
}
