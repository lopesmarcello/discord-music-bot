import type { ReactNode } from 'react';
import type { User } from '../api';
import { logout } from '../api';

interface AppShellProps {
  user: User;
  onLogout: () => void;
  guildId?: string;
  guildName?: string;
  guildIcon?: string | null;
  sidebar?: ReactNode;
  playerBar?: ReactNode;
  children: ReactNode;
}

export default function AppShell({
  user,
  onLogout,
  guildId,
  guildName,
  guildIcon,
  sidebar,
  playerBar,
  children,
}: AppShellProps) {
  const avatarUrl = user.avatar
    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=64`
    : `https://cdn.discordapp.com/embed/avatars/0.png`;

  const guildIconUrl =
    guildId && guildIcon
      ? `https://cdn.discordapp.com/icons/${guildId}/${guildIcon}.png?size=32`
      : null;

  const guildInitial = guildName ? guildName.charAt(0).toUpperCase() : null;

  async function handleLogout() {
    await logout();
    onLogout();
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: sidebar ? 'auto 1fr' : '1fr',
        height: '100vh',
        overflow: 'hidden',
      }}
    >
      {sidebar}

      {/* Main column: header + scrollable content */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <header
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
          }}
        >
          {/* Left: guild info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {guildIconUrl !== null ? (
              <img
                src={guildIconUrl}
                alt={guildName}
                style={{ width: 32, height: 32, borderRadius: '50%' }}
              />
            ) : guildInitial !== null ? (
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 14,
                  fontWeight: 700,
                  color: '#fff',
                  flexShrink: 0,
                }}
              >
                {guildInitial}
              </div>
            ) : null}
            {guildName && (
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {guildName}
              </span>
            )}
          </div>

          {/* Right: user avatar + username + logout */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img
              src={avatarUrl}
              alt={user.username}
              style={{ width: 32, height: 32, borderRadius: '50%' }}
            />
            <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>
              {user.username}
            </span>
            <button
              onClick={() => { void handleLogout(); }}
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: 13,
                padding: '6px 14px',
              }}
            >
              Logout
            </button>
          </div>
        </header>

        {/* Scrollable main content */}
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
            paddingBottom: 96,
          }}
        >
          {children}
        </main>
      </div>

      {/* Fixed player bar */}
      {playerBar && (
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            height: 80,
          }}
        >
          {playerBar}
        </div>
      )}
    </div>
  );
}
