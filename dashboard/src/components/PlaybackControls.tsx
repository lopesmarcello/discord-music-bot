import { useCallback, useEffect, useState } from 'react';
import type { PlaybackState } from '../api';
import { fetchPlayback, pausePlayback, resumePlayback, stopPlayback } from '../api';

interface PlaybackControlsProps {
  guildId: string;
  refreshTrigger?: number;
  onStopped?: () => void;
}

export default function PlaybackControls({ guildId, refreshTrigger, onStopped }: PlaybackControlsProps) {
  const [state, setState] = useState<PlaybackState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadState = useCallback(() => {
    fetchPlayback(guildId)
      .then(s => {
        setState(s);
        setError(null);
      })
      .catch(() => setError('Failed to load playback state.'));
  }, [guildId]);

  useEffect(() => {
    loadState();
    const id = setInterval(loadState, 5000);
    return () => clearInterval(id);
  }, [loadState]);

  useEffect(() => {
    if (refreshTrigger) loadState();
  }, [refreshTrigger, loadState]);

  async function handlePause() {
    setBusy(true);
    setError(null);
    try {
      await pausePlayback(guildId);
      loadState();
    } catch {
      setError('Pause failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleResume() {
    setBusy(true);
    setError(null);
    try {
      await resumePlayback(guildId);
      loadState();
    } catch {
      setError('Resume failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    setError(null);
    try {
      await stopPlayback(guildId);
      loadState();
      onStopped?.();
    } catch {
      setError('Stop failed.');
    } finally {
      setBusy(false);
    }
  }

  if (state === null) return null;

  const isActive = state === 'playing' || state === 'paused';

  return (
    <div style={styles.container}>
      <div style={styles.row}>
        <span style={styles.statusBadge(state)}>{stateLabel(state)}</span>

        <div style={styles.controls}>
          {state === 'playing' && (
            <button
              onClick={handlePause}
              disabled={busy}
              style={styles.controlButton}
              title="Pause"
            >
              ⏸ Pause
            </button>
          )}
          {state === 'paused' && (
            <button
              onClick={handleResume}
              disabled={busy}
              style={styles.controlButton}
              title="Resume"
            >
              ▶ Resume
            </button>
          )}
          {isActive && (
            <button
              onClick={handleStop}
              disabled={busy}
              style={styles.stopButton}
              title="Stop and disconnect"
            >
              ⏹ Stop
            </button>
          )}
        </div>
      </div>

      {error && <p style={styles.error}>{error}</p>}
    </div>
  );
}

function stateLabel(state: PlaybackState): string {
  if (state === 'playing') return 'Playing';
  if (state === 'paused') return 'Paused';
  return 'Stopped';
}

const badgeColors: Record<PlaybackState, string> = {
  playing: 'rgba(74,222,128,0.15)',
  paused: 'rgba(251,191,36,0.15)',
  stopped: 'rgba(255,255,255,0.07)',
};

const badgeBorder: Record<PlaybackState, string> = {
  playing: 'rgba(74,222,128,0.5)',
  paused: 'rgba(251,191,36,0.5)',
  stopped: 'rgba(255,255,255,0.15)',
};

const badgeText: Record<PlaybackState, string> = {
  playing: '#4ade80',
  paused: '#fbbf24',
  stopped: 'rgba(255,255,255,0.4)',
};

const styles = {
  container: {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: '16px 24px',
  } as React.CSSProperties,
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  } as React.CSSProperties,
  statusBadge: (state: PlaybackState): React.CSSProperties => ({
    background: badgeColors[state],
    border: `1px solid ${badgeBorder[state]}`,
    borderRadius: 20,
    color: badgeText[state],
    fontSize: 13,
    fontWeight: 600,
    padding: '4px 12px',
  }),
  controls: {
    display: 'flex',
    gap: 8,
    marginLeft: 'auto',
  } as React.CSSProperties,
  controlButton: {
    background: 'rgba(88,101,242,0.2)',
    border: '1px solid rgba(88,101,242,0.5)',
    borderRadius: 6,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    padding: '6px 16px',
  } as React.CSSProperties,
  stopButton: {
    background: 'rgba(248,113,113,0.15)',
    border: '1px solid rgba(248,113,113,0.4)',
    borderRadius: 6,
    color: '#f87171',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    padding: '6px 16px',
  } as React.CSSProperties,
  error: {
    color: '#f87171',
    fontSize: 13,
    margin: '8px 0 0',
  } as React.CSSProperties,
};
