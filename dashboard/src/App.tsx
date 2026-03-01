import { useEffect, useState } from 'react';
import type { User } from './api';
import { fetchMe } from './api';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import GuildPickerPage from './pages/GuildPickerPage';

type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'authenticated'; user: User };

const SESSION_GUILD_KEY = 'selected_guild';

function getQueryParam(name: string): string | undefined {
  return new URLSearchParams(window.location.search).get(name) ?? undefined;
}

function getSessionGuild(): string | undefined {
  return sessionStorage.getItem(SESSION_GUILD_KEY) ?? undefined;
}

function setSessionGuild(id: string): void {
  sessionStorage.setItem(SESSION_GUILD_KEY, id);
}

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: 'loading' });

  useEffect(() => {
    fetchMe()
      .then(user => {
        if (user) {
          setAuth({ status: 'authenticated', user });
        } else {
          setAuth({ status: 'unauthenticated' });
        }
      })
      .catch(() => setAuth({ status: 'unauthenticated' }));
  }, []);

  if (auth.status === 'loading') {
    return <LoadingScreen />;
  }

  if (auth.status === 'unauthenticated') {
    const guildId = getQueryParam('guild');
    const error = getQueryParam('error');
    return <LoginPage guildId={guildId} error={error} />;
  }

  // Persist guild selection in sessionStorage so refresh doesn't send the
  // user back to the picker.  URL param takes precedence; sessionStorage is
  // used as a fallback when the param is absent.
  const urlGuildId = getQueryParam('guild');
  let guildId: string | undefined;
  if (urlGuildId !== undefined) {
    setSessionGuild(urlGuildId);
    guildId = urlGuildId;
  } else {
    guildId = getSessionGuild();
  }

  const onLogout = () => {
    sessionStorage.removeItem(SESSION_GUILD_KEY);
    window.location.href = '/';
  };

  if (guildId === undefined) {
    return <GuildPickerPage user={auth.user} onLogout={onLogout} />;
  }

  return (
    <DashboardPage
      user={auth.user}
      guildId={guildId}
      onLogout={onLogout}
    />
  );
}

function LoadingScreen() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-base)',
      color: 'var(--text-muted)',
      fontSize: 16,
    }}>
      Loading…
    </div>
  );
}
