import { useCallback, useEffect, useState } from 'react';
import type { QueueData, Track } from '../api';
import { clearQueue, fetchQueue, skipTrack } from '../api';

interface QueueViewProps {
  guildId: string;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '–';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function QueueView({ guildId }: QueueViewProps) {
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

  async function handleSkip() {
    setBusy(true);
    try {
      await skipTrack(guildId);
      loadQueue();
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

  if (error) {
    return <div style={styles.error}>{error}</div>;
  }

  if (!queue) {
    return <div style={styles.loading}>Loading queue…</div>;
  }

  return (
    <div style={styles.container}>
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Now Playing</h2>
        {queue.current ? (
          <TrackRow track={queue.current} isCurrent />
        ) : (
          <p style={styles.emptyText}>Nothing is playing right now.</p>
        )}
        {queue.current && (
          <button
            onClick={handleSkip}
            disabled={busy}
            style={styles.actionButton}
          >
            Skip
          </button>
        )}
      </section>

      <section style={styles.section}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>
            Up Next {queue.tracks.length > 0 ? `(${queue.tracks.length})` : ''}
          </h2>
          {queue.tracks.length > 0 && (
            <button
              onClick={handleClear}
              disabled={busy}
              style={styles.clearButton}
            >
              Clear Queue
            </button>
          )}
        </div>
        {queue.tracks.length === 0 ? (
          <p style={styles.emptyText}>The queue is empty.</p>
        ) : (
          <ul style={styles.list}>
            {queue.tracks.map((track, i) => (
              <li key={`${track.url}-${i}`} style={styles.listItem}>
                <TrackRow track={track} index={i + 1} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

interface TrackRowProps {
  track: Track;
  isCurrent?: boolean;
  index?: number;
}

function TrackRow({ track, isCurrent, index }: TrackRowProps) {
  return (
    <div style={{ ...styles.trackRow, ...(isCurrent ? styles.trackRowCurrent : {}) }}>
      {index !== undefined && <span style={styles.trackIndex}>{index}</span>}
      <div style={styles.trackInfo}>
        <a
          href={track.url}
          target="_blank"
          rel="noreferrer"
          style={styles.trackTitle}
        >
          {track.title}
        </a>
        <span style={styles.trackDuration}>{formatDuration(track.duration)}</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 32,
  },
  section: {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 24,
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  sectionTitle: {
    margin: '0 0 16px',
    fontSize: 18,
    fontWeight: 600,
    color: '#ffffff',
  },
  emptyText: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 14,
    margin: 0,
  },
  loading: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 14,
    textAlign: 'center',
    padding: 48,
  },
  error: {
    color: '#f87171',
    fontSize: 14,
    textAlign: 'center',
    padding: 48,
  },
  actionButton: {
    marginTop: 16,
    background: 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: 6,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 13,
    padding: '6px 16px',
  },
  clearButton: {
    background: 'transparent',
    border: '1px solid rgba(248,113,113,0.5)',
    borderRadius: 6,
    color: '#f87171',
    cursor: 'pointer',
    fontSize: 13,
    padding: '4px 12px',
  },
  list: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  listItem: {
    margin: 0,
    padding: 0,
  },
  trackRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 12px',
    borderRadius: 8,
    background: 'rgba(255,255,255,0.03)',
  },
  trackRowCurrent: {
    background: 'rgba(88,101,242,0.2)',
    border: '1px solid rgba(88,101,242,0.4)',
  },
  trackIndex: {
    width: 24,
    textAlign: 'right',
    color: 'rgba(255,255,255,0.3)',
    fontSize: 13,
    flexShrink: 0,
  },
  trackInfo: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flex: 1,
    minWidth: 0,
    gap: 12,
  },
  trackTitle: {
    color: '#ffffff',
    textDecoration: 'none',
    fontSize: 14,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  trackDuration: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 13,
    flexShrink: 0,
  },
};
