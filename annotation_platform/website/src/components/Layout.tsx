import { NavLink, Outlet } from 'react-router-dom';
import { Shield, BarChart3, Search, FileCheck, Activity } from 'lucide-react';
import clsx from 'clsx';
import ExperimentPicker from './ExperimentPicker';
import AuthBar from './AuthBar';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: Activity },
  { to: '/models', label: 'Models', icon: BarChart3 },
  { to: '/probes', label: 'Probes', icon: Shield },
  { to: '/findings', label: 'Findings', icon: Search },
  { to: '/compliance', label: 'Compliance', icon: FileCheck },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col fixed h-full">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-indigo-500" />
            <div>
              <h1 className="text-lg font-bold text-white">ATLAS</h1>
              <p className="text-xs text-gray-500">Experiment Results</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <ExperimentPicker />
        <AuthBar />
        <div className="p-4 border-t border-gray-800">
          <p className="text-xs text-gray-600">2x2 Factorial Experiment</p>
        </div>
      </aside>
      <main className="flex-1 ml-64 p-8">
        <Outlet />
      </main>
    </div>
  );
}
