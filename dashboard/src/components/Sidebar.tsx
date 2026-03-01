import { useState } from 'react';

export type SidebarView = 'queue' | 'search';

interface SidebarProps {
  activeView: SidebarView;
  onViewChange: (view: SidebarView) => void;
  guildId: string;
  guildName: string;
  guildIcon: string | null;
}

const COLLAPSED_KEY = 'sidebar_collapsed';

export default function Sidebar({ activeView, onViewChange, guildId, guildName, guildIcon }: SidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem(COLLAPSED_KEY) === 'true';
  });

  function toggleCollapsed() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(COLLAPSED_KEY, String(next));
  }

  const guildIconUrl = guildIcon
    ? `https://cdn.discordapp.com/icons/${guildId}/${guildIcon}.png?size=64`
    : null;

  const guildInitial = guildName.charAt(0).toUpperCase();

  return (
    <nav
      style={{
        width: collapsed ? 64 : 220,
        minWidth: collapsed ? 64 : 220,
        height: 'calc(100vh - 80px)',
        background: 'var(--sidebar-bg)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease, min-width 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Top: Bot logo / wordmark */}
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: collapsed ? '0 18px' : '0 16px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}
      >
        <BotLogo />
        {!collapsed && (
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
            }}
          >
            MusicBot
          </span>
        )}
      </div>

      {/* Nav items */}
      <div style={{ flex: 1, padding: '12px 0', overflowY: 'auto' }}>
        <NavItem
          icon={<HomeIcon />}
          label="Queue"
          active={activeView === 'queue'}
          collapsed={collapsed}
          onClick={() => onViewChange('queue')}
        />
        <NavItem
          icon={<SearchIcon />}
          label="Search"
          active={activeView === 'search'}
          collapsed={collapsed}
          onClick={() => onViewChange('search')}
        />
      </div>

      {/* Bottom: guild info + collapse toggle */}
      <div
        style={{
          borderTop: '1px solid var(--border)',
          padding: '12px 0',
          flexShrink: 0,
        }}
      >
        {!collapsed && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              marginBottom: 4,
            }}
          >
            {guildIconUrl !== null ? (
              <img
                src={guildIconUrl}
                alt={guildName}
                style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0 }}
              />
            ) : (
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
            )}
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {guildName}
            </span>
          </div>
        )}
        <button
          onClick={toggleCollapsed}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            height: 36,
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
        </button>
      </div>
    </nav>
  );
}

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
}

function NavItem({ icon, label, active, collapsed, onClick }: NavItemProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={collapsed ? label : undefined}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        width: '100%',
        height: 44,
        padding: collapsed ? '0 20px' : '0 16px',
        background: active || hovered ? 'var(--bg-elevated)' : 'transparent',
        border: 'none',
        borderLeft: active ? '3px solid var(--accent)' : '3px solid transparent',
        color: active ? 'var(--text-primary)' : 'var(--text-muted)',
        cursor: 'pointer',
        fontSize: 14,
        fontWeight: active ? 600 : 400,
        textAlign: 'left',
        whiteSpace: 'nowrap',
        transition: 'background 0.15s, color 0.15s',
        boxSizing: 'border-box',
      }}
    >
      {icon}
      {!collapsed && <span>{label}</span>}
    </button>
  );
}

function BotLogo() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <circle cx="14" cy="14" r="14" fill="var(--accent)" />
      <path
        d="M8 18 L11 10 L14 16 L17 10 L20 18"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <path
        d="M3 12L12 3L21 12V21H15V15H9V21H3V12Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
      <path
        d="M21 21L16.65 16.65"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M15 18L9 12L15 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M9 18L15 12L9 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
