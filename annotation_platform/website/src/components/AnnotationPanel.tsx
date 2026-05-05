import { useCallback, useEffect, useState } from 'react';
import clsx from 'clsx';
import {
  type Annotation,
  type ReviewStatus,
  type ReviewSummary,
  REVIEW_STATUSES,
  castVote,
  createAnnotation,
  deleteAnnotation,
  getReview,
  listAnnotations,
  reviewStatusDefinition,
  reviewStatusColor,
  reviewStatusLabel,
  settlementColor,
  settlementLabel,
  updateAnnotation,
  withdrawVote,
} from '../lib/annotations';
import { type AuthUser, getCurrentUser, subscribeAuth } from '../lib/auth';

const LABEL_OPTIONS = ['confirmed', 'false_positive', 'needs_context', 'dup', 'interesting'];

interface Props {
  findingId: string;
  onReviewChange?: (r: ReviewSummary) => void;
  onAnnotationsChange?: (count: number) => void;
}

export default function AnnotationPanel({ findingId, onReviewChange, onAnnotationsChange }: Props) {
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [review, setReviewState] = useState<ReviewSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [user, setUser] = useState<AuthUser | null>(() => getCurrentUser());
  useEffect(() => subscribeAuth(() => setUser(getCurrentUser())), []);

  const [newNote, setNewNote] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [anns, rev] = await Promise.all([listAnnotations(findingId), getReview(findingId)]);
      setAnnotations(anns);
      setReviewState(rev);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load annotations');
    } finally {
      setLoading(false);
    }
  }, [findingId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const commitReview = (r: ReviewSummary) => {
    setReviewState(r);
    onReviewChange?.(r);
  };

  const onVote = async (status: ReviewStatus) => {
    if (!user) return;
    setSaving(true);
    try {
      // Toggle: clicking my current vote withdraws it.
      if (review?.my_vote?.status === status) {
        commitReview(await withdrawVote(findingId));
      } else {
        commitReview(await castVote(findingId, { status }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to cast vote');
    } finally {
      setSaving(false);
    }
  };

  const onAddAnnotation = async () => {
    if (!user) return;
    if (!newNote.trim() && !newLabel.trim()) return;
    setSaving(true);
    try {
      const ann = await createAnnotation(findingId, { note: newNote, label: newLabel });
      setAnnotations((prev) => {
        const next = [...prev, ann];
        onAnnotationsChange?.(next.length);
        return next;
      });
      setNewNote('');
      setNewLabel('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create annotation');
    } finally {
      setSaving(false);
    }
  };

  const onEdit = async (ann: Annotation, patch: Partial<Pick<Annotation, 'note' | 'label'>>) => {
    try {
      const updated = await updateAnnotation(ann.id, patch);
      setAnnotations((prev) => prev.map((a) => (a.id === ann.id ? updated : a)));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update annotation');
    }
  };

  const onDelete = async (ann: Annotation) => {
    try {
      await deleteAnnotation(ann.id);
      setAnnotations((prev) => {
        const next = prev.filter((a) => a.id !== ann.id);
        onAnnotationsChange?.(next.length);
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete annotation');
    }
  };

  const myStatus = review?.my_vote?.status ?? null;
  const settlement = review?.settlement ?? 'open';
  const settledStatus = review?.status ?? null;

  return (
    <div className="border-t border-gray-800 px-4 py-4 bg-gray-900/40">
      <div className="flex items-start justify-between gap-4 mb-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">
              Investigation & Voting
            </p>
            <span className={clsx('text-[10px] font-medium rounded px-2 py-0.5', settlementColor(settlement))}>
              {settlementLabel(settlement)}
              {review && review.distinct_voter_count > 0
                ? ` · ${review.distinct_voter_count} voter${review.distinct_voter_count === 1 ? '' : 's'}`
                : ''}
            </span>
            {settlement === 'settled' && settledStatus ? (
              <span className={clsx('text-[10px] font-medium rounded px-2 py-0.5', reviewStatusColor(settledStatus))}>
                → {reviewStatusLabel(settledStatus)}
              </span>
            ) : null}
          </div>

          {!user ? (
            <p className="text-xs text-gray-500 italic">
              Sign in to cast a vote. Two different annotators must agree on a status for a finding to be settled.
            </p>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-400">Your vote:</span>
              {REVIEW_STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => onVote(s)}
                  disabled={saving}
                  className={clsx(
                    'px-2.5 py-1 rounded-md text-xs font-medium transition-colors',
                    s === myStatus
                      ? reviewStatusColor(s)
                      : 'bg-gray-800/60 text-gray-500 hover:text-gray-300 border border-transparent'
                  )}
                  title={s === myStatus ? 'Click again to withdraw your vote' : `${reviewStatusLabel(s)}: ${reviewStatusDefinition(s)}`}
                >
                  {reviewStatusLabel(s)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Other annotators' votes */}
      {review && review.votes.length > 0 ? (
        <div className="mb-3 flex flex-wrap gap-2">
          {review.votes.map((v) => (
            <span
              key={v.id}
              className={clsx(
                'text-[11px] rounded-md px-2 py-1 border',
                v.user_id === user?.id ? 'border-indigo-600/60' : 'border-gray-700'
              )}
              title={`${v.username} voted at ${new Date(v.updated_at).toLocaleString()}`}
            >
              <span className="text-gray-400">{v.username}</span>{' '}
              <span className={clsx(
                'font-medium',
                v.status === 'confirmed_vulnerability' ? 'text-red-300'
                  : v.status === 'false_positive' ? 'text-green-300'
                  : v.status === 'false_negative' ? 'text-purple-300'
                  : v.status === 'needs_investigation' ? 'text-amber-300'
                  : 'text-gray-300'
              )}>
                {reviewStatusLabel(v.status)}
              </span>
            </span>
          ))}
        </div>
      ) : null}

      {error ? (
        <div className="text-xs text-red-400 mb-2 bg-red-900/20 border border-red-800/40 rounded px-2 py-1">
          {error}
        </div>
      ) : null}

      {/* Existing annotations */}
      <div className="space-y-2 mb-3">
        {loading && annotations.length === 0 ? (
          <p className="text-xs text-gray-600">Loading…</p>
        ) : annotations.length === 0 ? (
          <p className="text-xs text-gray-600 italic">No annotations yet.</p>
        ) : (
          annotations.map((a) => (
            <AnnotationRow
              key={a.id}
              ann={a}
              currentUser={user}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))
        )}
      </div>

      {/* New annotation form (auth required) */}
      {user ? (
        <div className="flex items-start gap-2 bg-gray-800/40 rounded-lg p-2 border border-gray-800">
          <select
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200"
          >
            <option value="">no label</option>
            {LABEL_OPTIONS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <textarea
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Add an investigation note…"
            rows={2}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200 resize-y"
          />
          <button
            onClick={onAddAnnotation}
            disabled={saving || (!newNote.trim() && !newLabel.trim())}
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium disabled:opacity-40"
          >
            {saving ? 'Saving…' : 'Add'}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function AnnotationRow({
  ann,
  currentUser,
  onEdit,
  onDelete,
}: {
  ann: Annotation;
  currentUser: AuthUser | null;
  onEdit: (a: Annotation, patch: { note?: string; label?: string }) => Promise<void>;
  onDelete: (a: Annotation) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState(ann.note);
  const [label, setLabel] = useState(ann.label);

  useEffect(() => {
    setNote(ann.note);
    setLabel(ann.label);
  }, [ann.note, ann.label]);

  const canEdit = !!currentUser && (!ann.author || ann.author === currentUser.username);

  const save = async () => {
    await onEdit(ann, { note, label });
    setEditing(false);
  };

  return (
    <div className="bg-gray-800/60 border border-gray-800 rounded-lg px-3 py-2 text-xs">
      <div className="flex items-center gap-2 mb-1">
        {ann.label ? (
          <span className="px-1.5 py-0.5 rounded bg-indigo-900/40 text-indigo-300 text-[10px] font-medium">
            {ann.label}
          </span>
        ) : null}
        <span className="text-gray-500">{ann.author || 'anonymous'}</span>
        <span className="text-gray-600">
          {new Date(ann.created_at).toLocaleString()}
          {ann.updated_at !== ann.created_at ? ' (edited)' : ''}
        </span>
        {canEdit ? (
          <div className="ml-auto flex gap-1">
            {editing ? (
              <>
                <button onClick={save} className="text-green-400 hover:text-green-300">
                  save
                </button>
                <button
                  onClick={() => {
                    setEditing(false);
                    setNote(ann.note);
                    setLabel(ann.label);
                  }}
                  className="text-gray-500 hover:text-gray-300"
                >
                  cancel
                </button>
              </>
            ) : (
              <>
                <button onClick={() => setEditing(true)} className="text-gray-400 hover:text-gray-200">
                  edit
                </button>
                <button onClick={() => onDelete(ann)} className="text-red-400 hover:text-red-300">
                  delete
                </button>
              </>
            )}
          </div>
        ) : null}
      </div>
      {editing ? (
        <div className="space-y-1.5">
          <select
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200"
          >
            <option value="">no label</option>
            {LABEL_OPTIONS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200"
          />
        </div>
      ) : (
        <p className="text-gray-300 whitespace-pre-wrap">
          {ann.note || <em className="text-gray-600">(no note)</em>}
        </p>
      )}
    </div>
  );
}
