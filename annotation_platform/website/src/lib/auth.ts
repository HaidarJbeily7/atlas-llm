// Minimal bearer-token auth client. Token + user are cached in localStorage
// and cleared on 401. Subscribers can react to login/logout changes.

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
const TOKEN_KEY = 'atlas.auth.token';
const USER_KEY = 'atlas.auth.user';
const CHANGE_EVENT = 'atlas:auth-change';

export interface AuthUser {
  id: number;
  username: string;
  created_at: string;
}

export interface LoginResponse {
  token: string;
  expires_at: string;
  user: AuthUser;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getCurrentUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

function emitChange() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  }
}

export function subscribeAuth(cb: () => void): () => void {
  if (typeof window === 'undefined') return () => {};
  window.addEventListener(CHANGE_EVENT, cb);
  return () => window.removeEventListener(CHANGE_EVENT, cb);
}

function setSession(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  emitChange();
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  emitChange();
}

/** Shared fetch that attaches the bearer token and clears the session on 401. */
export async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers ?? {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && token) {
    // Token likely expired / revoked.
    clearSession();
  }
  return res;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await authedFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  const data = await jsonOrThrow<LoginResponse>(res);
  setSession(data.token, data.user);
  return data.user;
}

export async function logout(): Promise<void> {
  try {
    await authedFetch('/api/auth/logout', { method: 'POST' });
  } catch {
    // ignore network errors on logout
  }
  clearSession();
}

export async function fetchMe(): Promise<AuthUser | null> {
  const token = getToken();
  if (!token) return null;
  const res = await authedFetch('/api/auth/me');
  if (res.status === 401) return null;
  return jsonOrThrow<AuthUser>(res);
}
