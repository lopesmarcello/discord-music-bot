export interface User {
  id: string;
  username: string;
  avatar: string | null;
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
