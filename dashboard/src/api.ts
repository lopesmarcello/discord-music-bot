export interface User {
  id: string;
  username: string;
  avatar: string | null;
}

export interface Guild {
  id: string;
  name: string;
  icon: string | null;
}

export interface Track {
  title: string;
  url: string;
  duration: number | null;
  source: string;
}

export interface QueueData {
  current: Track | null;
  tracks: Track[];
}

export interface SearchResult {
  title: string;
  url: string;
  duration: number | null;
  thumbnail: string;
}

/** Fetch the current authenticated user. Returns null if not logged in. */
export async function fetchMe(): Promise<User | null> {
  const res = await fetch('/auth/me');
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json() as Promise<User>;
}

/** Log out by clearing the session cookie. */
export async function logout(): Promise<void> {
  await fetch('/auth/logout', { method: 'POST' });
}

/** Build the Discord OAuth2 login URL for a given guild. */
export function loginUrl(guildId?: string): string {
  const params = guildId ? `?guild_id=${encodeURIComponent(guildId)}` : '';
  return `/auth/discord${params}`;
}

/** Fetch the current queue for a guild. */
export async function fetchQueue(guildId: string): Promise<QueueData> {
  const res = await fetch(`/api/queue?guild_id=${encodeURIComponent(guildId)}`);
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json() as Promise<QueueData>;
}

/** Skip the current track for a guild. Returns the updated queue state. */
export async function skipTrack(guildId: string): Promise<QueueData> {
  const res = await fetch(`/api/queue/skip?guild_id=${encodeURIComponent(guildId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  const data = await res.json() as { skipped: boolean; current: Track | null; tracks: Track[] };
  return { current: data.current, tracks: data.tracks };
}

/** Clear the upcoming queue for a guild. */
export async function clearQueue(guildId: string): Promise<void> {
  const res = await fetch(`/api/queue/clear?guild_id=${encodeURIComponent(guildId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
}

/** Search YouTube for videos matching a query. Returns up to `limit` results. */
export async function searchYouTube(query: string, limit = 5): Promise<SearchResult[]> {
  const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  const data = await res.json() as { results: SearchResult[] };
  return data.results;
}

export type PlaybackState = 'playing' | 'paused' | 'stopped';

/** Fetch the current playback state for a guild. */
export async function fetchPlayback(guildId: string): Promise<PlaybackState> {
  const res = await fetch(`/api/playback?guild_id=${encodeURIComponent(guildId)}`);
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  const data = await res.json() as { state: PlaybackState };
  return data.state;
}

/** Pause playback for a guild. */
export async function pausePlayback(guildId: string): Promise<void> {
  const res = await fetch(`/api/playback/pause?guild_id=${encodeURIComponent(guildId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
}

/** Resume playback for a guild. */
export async function resumePlayback(guildId: string): Promise<void> {
  const res = await fetch(`/api/playback/resume?guild_id=${encodeURIComponent(guildId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
}

/** Stop playback and disconnect the bot from the voice channel. */
export async function stopPlayback(guildId: string): Promise<void> {
  const res = await fetch(`/api/playback/stop?guild_id=${encodeURIComponent(guildId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
}

/** Add a track by URL to the guild queue. */
export async function addToQueue(guildId: string, url: string): Promise<void> {
  const res = await fetch(`/api/queue/add?guild_id=${encodeURIComponent(guildId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`Add to queue failed: ${res.status}`);
}

/** Fetch the list of guilds the bot is in. */
export async function fetchGuilds(): Promise<Guild[]> {
  const res = await fetch('/api/guilds');
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  const data = await res.json() as { guilds: Guild[] };
  return data.guilds;
}
