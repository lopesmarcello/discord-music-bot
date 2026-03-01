import { useCallback, useEffect, useState } from 'react';
import type { PlaybackState, Track } from '../api';
import { fetchPlayback, fetchQueue, pausePlayback, resumePlayback, skipTrack, stopPlayback } from '../api';

interface PlayerBarProps {
  guildId: string;
  onQueueChanged?: () => void;
}

export default function PlayerBar({ guildId, onQueueChanged }: PlayerBarProps) {
  const [playbackState, setPlaybackState] = useState<PlaybackState>('stopped');
  const [elapsedSeconds, setElapsedSeconds] = useState<number | null>(null);
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [busy, setBusy] = useState(false);

  const fetchData = useCallback(() => {
    Promise.all([fetchPlayback(guildId), fetchQueue(guildId)])
      .then(([playback, queue]) => {
        setPlaybackState(playback.state);
        setElapsedSeconds(playback.elapsedSeconds);
        setCurrentTrack(queue.current);
      })
      .catch(() => { /* silently ignore */ });
  }, [guildId]);

  // Poll every 5s
  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 5000);
    return () => clearInterval(id);
  }, [fetchData]);

  // Tick elapsed every second when playing
  useEffect(() => {
    if (playbackState !== 'playing') return;
    const id = setInterval(() => {
      setElapsedSeconds(prev => (prev !== null ? prev + 1 : prev));
    }, 1000);
    return () => clearInterval(id);
  }, [playbackState]);

  async function handlePlayPause() {
    setBusy(true);
    try {
      if (playbackState === 'playing') {
        await pausePlayback(guildId);
      } else {
        await resumePlayback(guildId);
      }
      fetchData();
    } catch { /* ignore */ } finally {
      setBusy(false);
    }
  }

  async function handleSkip() {
    setBusy(true);
    try {
      // Use the skip response to update state immediately (US-002).
      // Do NOT call fetchData() here — it races with the backend's transient
      // stopped state while _play_next resolves the next audio stream.
      // The 5-second poll will correct any remaining drift.
      const updated = await skipTrack(guildId);
      setCurrentTrack(updated.current);
      onQueueChanged?.();
    } catch { /* ignore */ } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      await stopPlayback(guildId);
      fetchData();
      onQueueChanged?.();
    } catch { /* ignore */ } finally {
      setBusy(false);
    }
  }

  const isStopped = playbackState === 'stopped';
  const duration = currentTrack?.duration ?? null;
  const progress =
    duration !== null && elapsedSeconds !== null && duration > 0
      ? Math.min(elapsedSeconds / duration, 1)
      : 0;

  const thumbnailUrl = currentTrack?.thumbnail || null;

  return (
    <div
      style={{
        height: 80,
        background: 'var(--player-bg)',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 16,
      }}
    >
      {/* Left: thumbnail + track info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: 250, flexShrink: 0 }}>
        {thumbnailUrl !== null ? (
          <img
            src={thumbnailUrl}
            alt="thumbnail"
            style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 4, flexShrink: 0 }}
          />
        ) : (
          <div
            style={{
              width: 56,
              height: 56,
              background: 'var(--bg-elevated)',
              borderRadius: 4,
              flexShrink: 0,
            }}
          />
        )}
        <div style={{ overflow: 'hidden' }}>
          {isStopped ? (
            <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>Nothing playing</span>
          ) : (
            <>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {currentTrack?.title ?? ''}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                {currentTrack?.source ?? ''}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Centre: controls */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
          opacity: isStopped ? 0.4 : 1,
        }}
      >
        <button
          onClick={() => { void handlePlayPause(); }}
          disabled={busy || isStopped}
          title={playbackState === 'playing' ? 'Pause' : 'Play'}
          style={controlButtonStyle}
        >
          {playbackState === 'playing' ? <PauseIcon /> : <PlayIcon />}
        </button>
        <button
          onClick={() => { void handleSkip(); }}
          disabled={busy || isStopped}
          title="Skip"
          style={controlButtonStyle}
        >
          <SkipIcon />
        </button>
        <button
          onClick={() => { void handleStop(); }}
          disabled={busy || isStopped}
          title="Stop"
          style={controlButtonStyle}
        >
          <StopIcon />
        </button>
      </div>

      {/* Right: progress bar */}
      <div style={{ width: 200, flexShrink: 0 }}>
        <div
          style={{
            height: 4,
            background: 'var(--bg-elevated)',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progress * 100}%`,
              background: 'var(--accent)',
              borderRadius: 2,
              transition: 'width 1s linear',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {formatTime(elapsedSeconds ?? 0)}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {duration !== null ? formatTime(duration) : '--:--'}
          </span>
        </div>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const remaining = s % 60;
  return `${m}:${remaining.toString().padStart(2, '0')}`;
}

const controlButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  color: 'var(--text-primary)',
  padding: 8,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

function PlayIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,3 19,12 5,21" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="4" width="4" height="16" />
      <rect x="14" y="4" width="4" height="16" />
    </svg>
  );
}

function SkipIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,4 15,12 5,20" />
      <rect x="16" y="4" width="3" height="16" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" />
    </svg>
  );
}
