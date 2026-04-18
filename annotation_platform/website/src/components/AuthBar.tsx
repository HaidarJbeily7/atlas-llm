import { useEffect, useState } from 'react';
import { LogIn, LogOut, User } from 'lucide-react';
import {
  type AuthUser,
  getCurrentUser,
  login,
  logout,
  subscribeAuth,
} from '../lib/auth';

export default function AuthBar() {
  const [user, setUser] = useState<AuthUser | null>(() => getCurrentUser());
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => subscribeAuth(() => setUser(getCurrentUser())), []);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      setOpen(false);
      setPassword('');
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/^\d+\s\w+:\s*/, '') : 'Failed');
    } finally {
      setBusy(false);
    }
  };

  if (user) {
    return (
      <div className="px-4 py-3 border-t border-gray-800 flex items-center gap-2">
        <User className="w-4 h-4 text-indigo-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-200 truncate">{user.username}</p>
          <p className="text-[10px] text-gray-600">signed in</p>
        </div>
        <button
          onClick={() => void logout()}
          title="Sign out"
          className="p-1.5 text-gray-500 hover:text-gray-200 hover:bg-gray-800 rounded"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="px-4 py-3 border-t border-gray-800 space-y-2">
      {!open ? (
        <button
          onClick={() => { setOpen(true); setError(null); }}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded"
        >
          <LogIn className="w-3.5 h-3.5" /> Sign in to annotate
        </button>
      ) : (
        <div className="space-y-2">
          <input
            autoFocus
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void submit(); }}
            placeholder="password"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200"
          />
          {error ? <p className="text-[10px] text-red-400">{error}</p> : null}
          <div className="flex gap-1">
            <button
              onClick={submit}
              disabled={busy || !username.trim() || !password}
              className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs rounded"
            >
              <LogIn className="w-3 h-3" />
              {busy ? '…' : 'Sign in'}
            </button>
            <button
              onClick={() => setOpen(false)}
              className="px-2 py-1.5 text-gray-500 hover:text-gray-300 text-xs"
            >
              cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
