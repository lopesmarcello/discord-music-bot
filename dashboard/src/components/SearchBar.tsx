import { useState } from 'react';
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

export default function SearchBar({ guildId, onAdded }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const r = await searchYouTube(query.trim());
      setResults(r);
    } catch {
      setError('Search failed. Please try again.');
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
    } catch {
      setError('Failed to add track to queue.');
    } finally {
      setAdding(null);
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Add to Queue</h2>
      <form onSubmit={handleSearch} style={styles.form}>
        <input
          style={styles.input}
          value={query}
          onChange={e => setQuery(e.target.value)}
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
          {results.map(result => (
            <li key={result.url} style={styles.resultItem}>
              <div style={styles.resultInfo}>
                <span style={styles.resultTitle}>{result.title}</span>
                {formatDuration(result.duration) && (
                  <span style={styles.resultDuration}>{formatDuration(result.duration)}</span>
                )}
              </div>
              <button
                onClick={() => handleAdd(result.url)}
                disabled={adding !== null}
                style={styles.addButton}
              >
                {adding === result.url ? 'Adding…' : '+ Add'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 24,
  },
  title: {
    margin: '0 0 16px',
    fontSize: 18,
    fontWeight: 600,
    color: '#ffffff',
  },
  form: {
    display: 'flex',
    gap: 8,
  },
  input: {
    flex: 1,
    background: 'rgba(255,255,255,0.08)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: 6,
    color: '#ffffff',
    fontSize: 14,
    padding: '8px 12px',
    outline: 'none',
  },
  searchButton: {
    background: '#5865f2',
    border: 'none',
    borderRadius: 6,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 600,
    padding: '8px 18px',
  },
  error: {
    color: '#f87171',
    fontSize: 13,
    margin: '8px 0 0',
  },
  emptyText: {
    color: 'rgba(255,255,255,0.4)',
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
    background: 'rgba(255,255,255,0.03)',
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
    color: '#ffffff',
    fontSize: 13,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  resultDuration: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 12,
    flexShrink: 0,
  },
  addButton: {
    background: 'rgba(88,101,242,0.3)',
    border: '1px solid rgba(88,101,242,0.5)',
    borderRadius: 6,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 12,
    padding: '4px 10px',
    flexShrink: 0,
  },
};
