import type { User } from '../api';
import { logout } from '../api';
import QueueView from '../components/QueueView';

interface DashboardPageProps {
  user: User;
  guildId?: string;
  onLogout: () => void;
}

export default function DashboardPage({ user, guildId, onLogout }: DashboardPageProps) {
  async function handleLogout() {
    await logout();
    onLogout();
  }

  const avatarUrl = user.avatar
    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=64`
    : `https://cdn.discordapp.com/embed/avatars/0.png`;

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>Music Bot Dashboard</h1>
        <div style={styles.userInfo}>
          <img src={avatarUrl} alt={user.username} style={styles.avatar} />
          <span style={styles.username}>{user.username}</span>
          <button onClick={handleLogout} style={styles.logoutButton}>
            Logout
          </button>
        </div>
      </header>

      <main style={styles.main}>
        {guildId ? (
          <QueueView guildId={guildId} />
        ) : (
          <div style={styles.noGuild}>
            <p>No guild selected. Please log in again with a guild link.</p>
          </div>
        )}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#1a1a2e',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: '#ffffff',
  },
  header: {
    background: 'rgba(255,255,255,0.05)',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
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
    color: 'rgba(255,255,255,0.8)',
  },
  logoutButton: {
    background: 'transparent',
    border: '1px solid rgba(255,255,255,0.3)',
    borderRadius: 6,
    color: 'rgba(255,255,255,0.7)',
    cursor: 'pointer',
    fontSize: 13,
    padding: '6px 14px',
  },
  main: {
    maxWidth: 900,
    margin: '0 auto',
    padding: '40px 24px',
  },
  noGuild: {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: '48px',
    textAlign: 'center',
    color: 'rgba(255,255,255,0.5)',
    fontSize: 15,
  },
};
