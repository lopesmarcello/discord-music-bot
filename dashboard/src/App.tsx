import { useEffect, useState } from 'react';
import type { User } from './api';
import { fetchMe } from './api';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';

type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'authenticated'; user: User };

function getQueryParam(name: string): string | undefined {
  return new URLSearchParams(window.location.search).get(name) ?? undefined;
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

  const guildId = getQueryParam('guild');
  return (
    <DashboardPage
      user={auth.user}
      guildId={guildId}
      onLogout={() => setAuth({ status: 'unauthenticated' })}
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
