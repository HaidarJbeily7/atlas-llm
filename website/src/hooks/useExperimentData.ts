import { useEffect, useState } from 'react';
import type { Summary, ModelAggregation } from '../types';
import { loadSummary, aggregateByModel } from '../lib/data';

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

  useEffect(() => {
    loadSummary()
      .then((data) => {
        setSummary(data);
        setModels(aggregateByModel(data.scans));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { summary, models, loading, error };
}
