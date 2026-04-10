import { useEffect, useState } from 'react';
import type { ScanResult, ModelSummary } from '../types';
import { loadAllScans, aggregateByModel } from '../lib/data';

interface ExperimentData {
  scans: ScanResult[];
  models: ModelSummary[];
  loading: boolean;
  error: string | null;
}

export function useExperimentData(): ExperimentData {
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAllScans()
      .then((data) => {
        setScans(data);
        setModels(aggregateByModel(data));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { scans, models, loading, error };
}
