import type { ReactNode } from 'react';
import clsx from 'clsx';

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export default function StatCard({ label, value, sub, icon, trend, className }: Props) {
  return (
    <div className={clsx('card', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
          {sub && (
            <p
              className={clsx(
                'text-xs mt-1',
                trend === 'up' && 'text-green-400',
                trend === 'down' && 'text-red-400',
                (!trend || trend === 'neutral') && 'text-gray-500'
              )}
            >
              {sub}
            </p>
          )}
        </div>
        {icon && <div className="text-gray-600">{icon}</div>}
      </div>
    </div>
  );
}
