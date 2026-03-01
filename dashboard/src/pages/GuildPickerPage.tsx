import { useEffect, useState } from 'react';
import type { Guild, User } from '../api';
import { fetchGuilds } from '../api';

interface GuildPickerPageProps {
  user: User;
  onLogout: () => void;
}

export default function GuildPickerPage({ user, onLogout }: GuildPickerPageProps) {
  const [guilds, setGuilds] = useState<Guild[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchGuilds()
      .then(data => setGuilds(data))
      .catch(() => setError(true));
  }, []);

  const avatarUrl = user.avatar
    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=64`
    : `https://cdn.discordapp.com/embed/avatars/0.png`;

  function handleGuildClick(guildId: string) {
    window.location.href = `/?guild=${encodeURIComponent(guildId)}`;
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>Select a Server</h1>
        <div style={styles.userInfo}>
          <img src={avatarUrl} alt={user.username} style={styles.avatar} />
          <span style={styles.username}>{user.username}</span>
          <button onClick={onLogout} style={styles.logoutButton}>Logout</button>
        </div>
      </header>

      <main style={styles.main}>
        {error ? (
          <div style={styles.message}>Could not load servers. Please try again.</div>
        ) : guilds === null ? (
          <div style={styles.grid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={styles.skeletonCard} />
            ))}
          </div>
        ) : guilds.length === 0 ? (
          <div style={styles.message}>The bot is not in any servers yet.</div>
        ) : (
          <div style={styles.grid}>
            {guilds.map(guild => (
              <GuildCard key={guild.id} guild={guild} onClick={() => handleGuildClick(guild.id)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function GuildCard({ guild, onClick }: { guild: Guild; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);

  const iconUrl = guild.icon
    ? `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png?size=64`
    : null;

  const initial = guild.name.charAt(0).toUpperCase();

  return (
    <div
      style={{
        ...styles.card,
        ...(hovered ? styles.cardHover : {}),
      }}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {iconUrl ? (
        <img src={iconUrl} alt={guild.name} style={styles.guildIcon} />
      ) : (
        <div style={styles.guildInitial}>{initial}</div>
      )}
      <span style={styles.guildName}>{guild.name}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: 'var(--bg-base)',
    color: 'var(--text-primary)',
  },
  header: {
    background: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border)',
    padding: '0 24px',
    height: 64,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    margin: 0,
    fontSize: 20,
    fontWeight: 700,
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: '50%',
  },
  username: {
    fontSize: 14,
    color: 'var(--text-muted)',
  },
  logoutButton: {
    background: 'transparent',
    border: '1px solid var(--border)',
    borderRadius: 6,
    color: 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: 13,
    padding: '6px 14px',
  },
  main: {
    maxWidth: 960,
    margin: '0 auto',
    padding: '48px 24px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: 16,
  },
  card: {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '24px 16px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12,
    cursor: 'pointer',
    transition: 'border-color 0.15s, background 0.15s',
  },
  cardHover: {
    borderColor: 'var(--accent)',
    background: 'var(--bg-elevated)',
  },
  guildIcon: {
    width: 64,
    height: 64,
    borderRadius: '50%',
  },
  guildInitial: {
    width: 64,
    height: 64,
    borderRadius: '50%',
    background: 'var(--accent)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 28,
    fontWeight: 700,
    color: '#ffffff',
  },
  guildName: {
    fontSize: 13,
    fontWeight: 600,
    textAlign: 'center',
    color: 'var(--text-primary)',
    wordBreak: 'break-word',
  },
  skeletonCard: {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    height: 140,
    opacity: 0.5,
  },
  message: {
    textAlign: 'center',
    color: 'var(--text-muted)',
    fontSize: 15,
    padding: '64px 0',
  },
};
