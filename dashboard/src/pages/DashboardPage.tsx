import { useEffect, useState } from 'react';
import type { Guild, User } from '../api';
import { fetchGuilds } from '../api';
import AppShell from '../components/AppShell';
import Sidebar from '../components/Sidebar';
import type { SidebarView } from '../components/Sidebar';
import PlaybackControls from '../components/PlaybackControls';
import QueueView from '../components/QueueView';
import SearchBar from '../components/SearchBar';

interface DashboardPageProps {
  user: User;
  guildId: string;
  onLogout: () => void;
}

export default function DashboardPage({ user, guildId, onLogout }: DashboardPageProps) {
  const [queueRefreshKey, setQueueRefreshKey] = useState(0);
  const [activeView, setActiveView] = useState<SidebarView>('queue');
  const [guild, setGuild] = useState<Guild | null>(null);

  useEffect(() => {
    fetchGuilds()
      .then(guilds => {
        const found = guilds.find(g => g.id === guildId) ?? null;
        setGuild(found);
      })
      .catch(() => {
        // guild info unavailable, continue without it
      });
  }, [guildId]);

  return (
    <AppShell
      user={user}
      onLogout={onLogout}
      guildId={guildId}
      guildName={guild?.name}
      guildIcon={guild?.icon}
      sidebar={
        <Sidebar
          activeView={activeView}
          onViewChange={setActiveView}
          guildId={guildId}
          guildName={guild?.name ?? ''}
          guildIcon={guild?.icon ?? null}
        />
      }
    >
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px' }}>
        {activeView === 'queue' ? (
          <>
            <PlaybackControls
              guildId={guildId}
              refreshTrigger={queueRefreshKey}
              onStopped={() => setQueueRefreshKey(k => k + 1)}
            />
            <QueueView guildId={guildId} refreshTrigger={queueRefreshKey} />
          </>
        ) : (
          <SearchBar
            guildId={guildId}
            onAdded={() => setQueueRefreshKey(k => k + 1)}
          />
        )}
      </div>
    </AppShell>
  );
}
