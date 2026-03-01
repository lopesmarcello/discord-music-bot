import { useRef, useState } from 'react';
import type { SearchResult } from '../api';
import { addToQueue, searchYouTube } from '../api';

interface SearchBarProps {
  guildId: string;
  onAdded?: () => void;
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function ResultThumbnail({ url, title }: { url: string; title: string }) {
  const [failed, setFailed] = useState(false);
  const letter = title.charAt(0).toUpperCase();
  if (!url || failed) {
    return <div style={styles.thumbPlaceholder}>{letter}</div>;
  }
  return <img src={url} alt="" style={styles.thumb} onError={() => setFailed(true)} />;
}

export default function SearchBar({ guildId, onAdded }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const addedTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const r = await searchYouTube(query.trim());
      setResults(r);
    } catch {
      setError('Search unavailable. Please try again later.');
    } finally {
      setSearching(false);
    }
  }

  async function handleAdd(url: string) {
    setAdding(url);
    setError(null);
    try {
      await addToQueue(guildId, url);
      onAdded?.();
      setAdded(prev => new Set(prev).add(url));
      const timer = setTimeout(() => {
        setAdded(prev => {
          const next = new Set(prev);
          next.delete(url);
          return next;
        });
        addedTimers.current.delete(url);
      }, 2000);
      addedTimers.current.set(url, timer);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '';
      if (msg.toLowerCase().includes('voice channel')) {
        setError('The bot is not in a voice channel. Use /join in Discord first, then try again.');
      } else {
        setError('Failed to add track to queue.');
      }
    } finally {
      setAdding(null);
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Add to Queue</h2>
      <form onSubmit={handleSearch} style={styles.form}>
        <input
          style={{ ...styles.input, ...(focused ? styles.inputFocused : {}) }}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Search YouTube…"
          disabled={searching}
        />
        <button
          type="submit"
          disabled={searching || !query.trim()}
          style={styles.searchButton}
        >
          {searching ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <p style={styles.error}>{error}</p>}

      {results !== null && results.length === 0 && (
        <p style={styles.emptyText}>No results found.</p>
      )}

      {results && results.length > 0 && (
        <ul style={styles.resultList}>
          {results.map(result => {
            const isAdding = adding === result.url;
            const isAdded = added.has(result.url);
            return (
              <li key={result.url} style={styles.resultItem}>
                <ResultThumbnail url={result.thumbnail} title={result.title} />
                <div style={styles.resultInfo}>
                  <span style={styles.resultTitle}>{result.title}</span>
                  {formatDuration(result.duration) && (
                    <span style={styles.resultDuration}>{formatDuration(result.duration)}</span>
                  )}
                </div>
                <button
                  onClick={() => handleAdd(result.url)}
                  disabled={adding !== null || isAdded}
                  style={{
                    ...styles.addButton,
                    ...(isAdding ? styles.addButtonAdding : {}),
                    ...(isAdded ? styles.addButtonAdded : {}),
                  }}
                >
                  {isAdding ? 'Adding…' : isAdded ? 'Added ✓' : '+ Add'}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: 24,
  },
  title: {
    margin: '0 0 16px',
    fontSize: 18,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  form: {
    display: 'flex',
    gap: 8,
  },
  input: {
    flex: 1,
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text-primary)',
    fontSize: 14,
    padding: '10px 14px',
    outline: 'none',
    transition: 'box-shadow 0.15s, border-color 0.15s',
  },
  inputFocused: {
    boxShadow: '0 0 0 2px var(--accent)',
    borderColor: 'var(--accent)',
  },
  searchButton: {
    background: 'var(--accent)',
    border: 'none',
    borderRadius: 8,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 600,
    padding: '10px 20px',
    flexShrink: 0,
  },
  error: {
    color: '#f87171',
    fontSize: 13,
    margin: '8px 0 0',
  },
  emptyText: {
    color: 'var(--text-muted)',
    fontSize: 13,
    margin: '12px 0 0',
  },
  resultList: {
    listStyle: 'none',
    margin: '12px 0 0',
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  resultItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 10px',
    borderRadius: 6,
    background: 'var(--bg-surface)',
  },
  thumb: {
    width: 48,
    height: 48,
    borderRadius: 4,
    objectFit: 'cover',
    flexShrink: 0,
  },
  thumbPlaceholder: {
    width: 48,
    height: 48,
    borderRadius: 4,
    background: 'var(--bg-elevated)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    fontWeight: 700,
    color: 'var(--text-muted)',
    flexShrink: 0,
  },
  resultInfo: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    minWidth: 0,
    gap: 12,
  },
  resultTitle: {
    color: 'var(--text-primary)',
    fontSize: 14,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  resultDuration: {
    color: 'var(--text-muted)',
    fontSize: 12,
    flexShrink: 0,
  },
  addButton: {
    background: 'transparent',
    border: '1px solid var(--accent)',
    borderRadius: 6,
    color: 'var(--accent)',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
    padding: '6px 12px',
    flexShrink: 0,
    transition: 'background 0.15s, color 0.15s',
  },
  addButtonAdding: {
    background: 'var(--accent)',
    color: '#ffffff',
  },
  addButtonAdded: {
    background: 'var(--accent)',
    color: '#ffffff',
    opacity: 0.8,
  },
};
