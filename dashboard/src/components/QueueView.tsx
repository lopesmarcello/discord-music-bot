import { useCallback, useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import type { QueueData, Track } from '../api';
import { clearQueue, fetchQueue, skipTrack } from '../api';

interface QueueViewProps {
  guildId: string;
  refreshTrigger?: number;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '–';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function SkipIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
    </svg>
  );
}

function TrackThumbnail({ track, size }: { track: Track; size: number }) {
  const [imgError, setImgError] = useState(false);
  const letter = track.title.charAt(0).toUpperCase() || '?';
  const common: CSSProperties = {
    width: size,
    height: size,
    borderRadius: 4,
    flexShrink: 0,
    objectFit: 'cover',
  };
  if (track.thumbnail && !imgError) {
    return (
      <img
        src={track.thumbnail}
        alt=""
        style={common}
        onError={() => setImgError(true)}
      />
    );
  }
  return (
    <div
      style={{
        ...common,
        background: 'var(--bg-elevated)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-muted)',
        fontSize: size * 0.4,
        fontWeight: 600,
      }}
    >
      {letter}
    </div>
  );
}

interface TrackRowProps {
  track: Track;
  isCurrent?: boolean;
  index?: number;
  onSkip?: () => void;
  busy?: boolean;
}

function TrackRow({ track, isCurrent, index, onSkip, busy }: TrackRowProps) {
  const [hovered, setHovered] = useState(false);

  const rowStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 12px',
    paddingLeft: isCurrent ? 9 : 12,
    borderRadius: 6,
    background: isCurrent ? 'var(--bg-elevated)' : 'var(--bg-surface)',
    borderLeft: isCurrent ? '3px solid var(--accent)' : '3px solid transparent',
    outline: !isCurrent && hovered ? '1px solid var(--border)' : 'none',
    transition: 'background 0.15s',
    marginBottom: 2,
  };

  return (
    <div
      style={rowStyle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span style={styles.indexCol}>
        {index !== undefined ? index : null}
      </span>
      <TrackThumbnail track={track} size={40} />
      <span style={styles.titleCol}>
        <a href={track.url} target="_blank" rel="noreferrer" style={styles.trackLink}>
          {track.title}
        </a>
      </span>
      <span style={styles.durationCol}>{formatDuration(track.duration)}</span>
      {isCurrent && onSkip && (
        <button
          onClick={onSkip}
          disabled={busy}
          style={styles.skipIconButton}
          title="Skip"
        >
          <SkipIcon />
        </button>
      )}
    </div>
  );
}

export default function QueueView({ guildId, refreshTrigger }: QueueViewProps) {
  const [queue, setQueue] = useState<QueueData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadQueue = useCallback(() => {
    fetchQueue(guildId)
      .then(data => {
        setQueue(data);
        setError(null);
      })
      .catch(() => setError('Failed to load queue. Is the bot online?'));
  }, [guildId]);

  useEffect(() => {
    loadQueue();
    const id = setInterval(loadQueue, 5000);
    return () => clearInterval(id);
  }, [loadQueue]);

  useEffect(() => {
    if (refreshTrigger) loadQueue();
  }, [refreshTrigger, loadQueue]);

  async function handleSkip() {
    setBusy(true);
    try {
      const updated = await skipTrack(guildId);
      setQueue(updated);
      setError(null);
    } catch {
      setError('Skip failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleClear() {
    setBusy(true);
    try {
      await clearQueue(guildId);
      loadQueue();
    } catch {
      setError('Clear failed.');
    } finally {
      setBusy(false);
    }
  }

  if (!queue) {
    return (
      <div style={styles.loadingOrError}>
        {error ?? 'Loading queue…'}
      </div>
    );
  }

  const isEmpty = queue.current === null && queue.tracks.length === 0;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.headerTitle}>Queue</span>
        {queue.tracks.length > 0 && (
          <button
            onClick={() => { void handleClear(); }}
            disabled={busy}
            style={styles.clearButton}
          >
            Clear Queue
          </button>
        )}
      </div>

      {error && <div style={styles.errorBanner}>{error}</div>}

      {isEmpty ? (
        <div style={styles.emptyState}>Queue is empty</div>
      ) : (
        <>
          {queue.current !== null && (
            <TrackRow
              track={queue.current}
              isCurrent
              onSkip={() => { void handleSkip(); }}
              busy={busy}
            />
          )}
          {queue.tracks.length > 0 && (
            <div style={styles.list}>
              {queue.tracks.map((track, i) => (
                <TrackRow
                  key={`${track.url}-${i}`}
                  track={track}
                  index={i + 1}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  clearButton: {
    background: 'transparent',
    border: '1px solid var(--accent)',
    borderRadius: 6,
    color: 'var(--accent)',
    cursor: 'pointer',
    fontSize: 12,
    padding: '4px 12px',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
  },
  emptyState: {
    color: 'var(--text-muted)',
    fontSize: 14,
    textAlign: 'center',
    padding: '48px 0',
  },
  loadingOrError: {
    color: 'var(--text-muted)',
    fontSize: 14,
    textAlign: 'center',
    padding: 48,
  },
  errorBanner: {
    color: '#f87171',
    fontSize: 13,
    padding: '8px 12px',
    background: 'rgba(248,113,113,0.1)',
    borderRadius: 6,
    marginBottom: 4,
  },
  indexCol: {
    width: 24,
    textAlign: 'right',
    color: 'var(--text-muted)',
    fontSize: 13,
    flexShrink: 0,
  },
  titleCol: {
    flex: 1,
    minWidth: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  trackLink: {
    color: 'var(--text-primary)',
    textDecoration: 'none',
    fontSize: 14,
    display: 'block',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  durationCol: {
    color: 'var(--text-muted)',
    fontSize: 13,
    flexShrink: 0,
  },
  skipIconButton: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    padding: 4,
    borderRadius: 4,
    flexShrink: 0,
  },
};
