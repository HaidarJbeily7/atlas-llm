import { useEffect, useState } from 'react';
import { listExperiments, type ExperimentMeta } from '../lib/experiments';
import { getActiveExperiment, setActiveExperiment } from '../lib/data';

export default function ExperimentPicker() {
  const [experiments, setExperiments] = useState<ExperimentMeta[] | null>(null);
  const [selected, setSelected] = useState<string>(getActiveExperiment() ?? '');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listExperiments()
      .then((rows) => {
        setExperiments(rows);
        setError(null);
      })
      .catch(() => {
        setExperiments([]);
        setError('backend unreachable');
      });
  }, []);

  // Hide the picker entirely when no backend / no experiments — existing static flow handles it.
  if (experiments === null) return null;
  if (error || experiments.length === 0) return null;

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value;
    setSelected(v);
    setActiveExperiment(v === '' ? null : v);
  };

  return (
    <div className="px-4 py-3 border-t border-gray-800 space-y-1">
      <label className="text-[10px] text-gray-500 uppercase tracking-wider block">Experiment</label>
      <select
        value={selected}
        onChange={onChange}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200"
      >
        <option value="">Latest ({experiments[0].id})</option>
        {experiments.map((e) => (
          <option key={e.id} value={e.id}>
            {e.id} · {e.finding_count} findings
          </option>
        ))}
      </select>
    </div>
  );
}
