import { loginUrl } from '../api';

interface LoginPageProps {
  guildId?: string;
  error?: string;
}

export default function LoginPage({ guildId, error }: LoginPageProps) {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Music Bot Dashboard</h1>
        <p style={styles.subtitle}>Control your Discord music bot from the web</p>

        {error && (
          <div style={styles.error}>
            {errorMessage(error)}
          </div>
        )}

        <a href={loginUrl(guildId)} style={styles.loginButton}>
          <DiscordIcon />
          Login with Discord
        </a>
      </div>
    </div>
  );
}

function errorMessage(code: string): string {
  switch (code) {
    case 'invalid_code': return 'Authentication failed. Please try again.';
    case 'not_in_guild': return 'You are not a member of the required server.';
    default: return 'An error occurred. Please try again.';
  }
}

function DiscordIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 127.14 96.36"
      fill="currentColor"
      aria-hidden="true"
      style={{ marginRight: 10, verticalAlign: 'middle' }}
    >
      <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z" />
    </svg>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  card: {
    background: 'rgba(255,255,255,0.05)',
    backdropFilter: 'blur(10px)',
    borderRadius: 16,
    padding: '48px 40px',
    textAlign: 'center',
    maxWidth: 400,
    width: '100%',
    margin: '0 16px',
    border: '1px solid rgba(255,255,255,0.1)',
  },
  title: {
    color: '#ffffff',
    fontSize: 28,
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 15,
    margin: '0 0 32px',
  },
  error: {
    background: 'rgba(220,53,69,0.2)',
    border: '1px solid rgba(220,53,69,0.5)',
    borderRadius: 8,
    color: '#ff6b7a',
    padding: '10px 16px',
    marginBottom: 20,
    fontSize: 14,
  },
  loginButton: {
    display: 'inline-flex',
    alignItems: 'center',
    background: '#5865f2',
    color: '#ffffff',
    textDecoration: 'none',
    padding: '14px 28px',
    borderRadius: 8,
    fontSize: 16,
    fontWeight: 600,
    transition: 'background 0.2s',
  },
};
