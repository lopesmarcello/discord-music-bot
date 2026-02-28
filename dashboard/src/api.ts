export interface User {
  id: string;
  username: string;
  avatar: string | null;
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

/** Skip the current track for a guild. */
export async function skipTrack(guildId: string): Promise<void> {
  const res = await fetch(`/api/queue/skip?guild_id=${encodeURIComponent(guildId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
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

/** Add a track by URL to the guild queue. */
export async function addToQueue(guildId: string, url: string): Promise<void> {
  const res = await fetch(`/api/queue/add?guild_id=${encodeURIComponent(guildId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`Add to queue failed: ${res.status}`);
}
