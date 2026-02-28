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
