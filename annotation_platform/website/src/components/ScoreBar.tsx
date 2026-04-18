import clsx from 'clsx';

interface Props {
  value: number;
  max?: number;
  label?: string;
  size?: 'sm' | 'md';
}

function getColor(pct: number) {
  if (pct >= 80) return 'bg-green-500';
  if (pct >= 60) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function ScoreBar({ value, max = 100, label, size = 'md' }: Props) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">{label}</span>
          <span className="text-gray-300 font-medium">{value.toFixed(1)}%</span>
        </div>
      )}
      <div
        className={clsx(
          'w-full bg-gray-800 rounded-full overflow-hidden',
          size === 'sm' ? 'h-1.5' : 'h-2.5'
        )}
      >
        <div
          className={clsx('h-full rounded-full transition-all', getColor(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
