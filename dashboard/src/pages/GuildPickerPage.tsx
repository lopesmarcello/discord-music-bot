import { useEffect, useState } from 'react';
import type { Guild, User } from '../api';
import { fetchGuilds } from '../api';
import AppShell from '../components/AppShell';

interface GuildPickerPageProps {
  user: User;
  onLogout: () => void;
}

export default function GuildPickerPage({ user, onLogout }: GuildPickerPageProps) {
  const [guilds, setGuilds] = useState<Guild[] | null>(null);
  const [error, setError] = useState(false);

  function handleGuildClick(guildId: string) {
    window.location.href = `/?guild=${encodeURIComponent(guildId)}`;
  }

  useEffect(() => {
    fetchGuilds()
      .then(data => {
        // Auto-select when the user shares exactly one guild with the bot
        if (data.length === 1) {
          handleGuildClick(data[0].id);
        } else {
          setGuilds(data);
        }
      })
      .catch(() => setError(true));
  }, []);

  return (
    <AppShell user={user} onLogout={onLogout}>
      <div style={styles.main}>
        <h1 style={styles.title}>Select a Server</h1>
        {error ? (
          <div style={styles.message}>Could not load servers. Please try again.</div>
        ) : guilds === null ? (
          <div style={styles.grid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={styles.skeletonCard} />
            ))}
          </div>
        ) : guilds.length === 0 ? (
          <div style={styles.message}>No common servers found. Make sure the bot is in a server you belong to.</div>
        ) : (
          <div style={styles.grid}>
            {guilds.map(guild => (
              <GuildCard key={guild.id} guild={guild} onClick={() => handleGuildClick(guild.id)} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
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
  main: {
    maxWidth: 960,
    margin: '0 auto',
    padding: '48px 24px',
  },
  title: {
    margin: '0 0 32px 0',
    fontSize: 24,
    fontWeight: 700,
    color: 'var(--text-primary)',
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
