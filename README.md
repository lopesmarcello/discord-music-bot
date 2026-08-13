# Discord Music Bot

[![CI](https://github.com/lopesmarcello/discord-music-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/lopesmarcello/discord-music-bot/actions/workflows/ci.yml)

A self-hosted Discord music bot written in Python that streams audio from YouTube and SoundCloud into voice channels. Supports slash commands (`/play`) and prefix commands (`!play`), and ships with a browser-based web dashboard for queue management and playback control.

## Features

- Stream audio from YouTube URLs, YouTube search queries, and SoundCloud URLs
- Playback controls: play, pause, resume, skip, stop
- Per-guild song queue with add / view / clear operations
- Slash commands (`/play`) and prefix commands (`!play`)
- Web dashboard: browser-based queue view, YouTube search, and playback controls
- Discord OAuth2 authentication for the dashboard — no extra accounts needed
- Fully containerised with Docker Compose for easy self-hosting

## Architecture

```
Discord API
    │  WebSocket (bot events & commands)
    ▼
┌─────────────────────────────────────┐
│              bot (Python)           │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  discord.py  │  │ aiohttp API │ │
│  │  Music Cog   │  │  :8080      │ │
│  └──────────────┘  └──────┬──────┘ │
└──────────────────────────│──────────┘
                            │  REST / JSON
                            ▼
┌─────────────────────────────────────┐
│        dashboard (React + nginx)    │
│  nginx :3000  →  proxies /api/* and │
│                  /auth/* to :8080   │
└─────────────────────────────────────┘
                            │
                            ▼
                     Browser (user)
```

> The dashboard communicates exclusively with the bot's HTTP API. The bot holds the voice connections and queue state. Authentication is handled by Discord OAuth2 — the bot issues a JWT session cookie after the OAuth2 flow completes.

## Requirements

- Python 3.11+
- FFmpeg (must be on `PATH`)
- Node.js 20.19+ (only needed to build the dashboard outside Docker)
- Docker + Compose plugin (recommended for deployment)

## Quick Start (Local Development)

### 1. Clone the repository

```bash
git clone https://github.com/lopesmarcello/discord-music-bot
cd discord-music-bot
```

### 2. Install Python dependencies

```bash
# Install the bot and all dev tools (pytest, ruff)
pip install -e ".[dev]"
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Environment Variables](#environment-variables) below for details):

```dotenv
DISCORD_TOKEN=your_discord_bot_token
COMMAND_PREFIX=!
API_PORT=8080
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
JWT_SECRET=your_jwt_secret
YOUTUBE_API_KEY=                    # optional
```

### 4. Run the bot

```bash
python -m bot
```

This starts the Discord bot and the HTTP API server together (default port 8080).

### 5. Run the dashboard (optional, without Docker)

```bash
cd dashboard
npm install
npm run dev          # dev server at http://localhost:5173
```

Or build for production:

```bash
npm run build        # output to dashboard/dist/
```

### 6. Open the dashboard

Navigate to `http://localhost:3000?guild=YOUR_GUILD_ID` (or the dev server URL) and log in with Discord.

---

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | Bot token from the [Discord Developer Portal](https://discord.com/developers/applications) |
| `COMMAND_PREFIX` | No | Prefix for legacy text commands (default `!`) |
| `API_PORT` | No | HTTP API port (default `8080`) |
| `DISCORD_CLIENT_ID` | Yes | OAuth2 application Client ID |
| `DISCORD_CLIENT_SECRET` | Yes | OAuth2 application Client Secret |
| `DISCORD_REDIRECT_URI` | Yes | OAuth2 redirect URI (e.g. `http://localhost:3000/auth/callback`) |
| `JWT_SECRET` | Yes | Secret key for signing session cookies — use `openssl rand -hex 32` |
| `DASHBOARD_URL` | No | Base URL the bot redirects to after OAuth2 (default `http://localhost:3000`) |
| `YOUTUBE_API_KEY` | No | YouTube Data API v3 key for search (falls back to yt-dlp without it) |

### Getting credentials

- **Discord token**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications) and enable **Message Content Intent** under Bot settings.
- **Client ID / Secret**: In the same application, go to **OAuth2 → General**.
- **Redirect URI**: Add your callback URL to **OAuth2 → Redirects** (e.g. `http://localhost:3000/auth/callback`).
- **JWT secret**: Any long random string — `openssl rand -hex 32` works well.
- **YouTube API key**: Create a project at [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → enable YouTube Data API v3.

---

## Running Tests & Linting

```bash
# Run all tests with coverage (CI enforces >= 70%)
pytest --cov --cov-report=term-missing --cov-fail-under=70

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Lint check (must pass before committing — covers bot/ and tests/)
ruff check bot/ tests/

# Format check (must pass before committing)
ruff format --check bot/ tests/

# Auto-fix lint violations
ruff check --fix bot/ tests/

# Auto-format
ruff format bot/ tests/
```

### Dashboard type-check

```bash
cd dashboard
npm run typecheck
```

---

## Commands

| Command | Alias | Description |
| --- | --- | --- |
| `/play <query>` | `!play <query>` | Play a song by URL or search query |
| `/pause` | `!pause` | Pause currently playing audio |
| `/resume` | `!resume` | Resume paused audio |
| `/skip` | `!skip` | Skip to the next song |
| `/stop` | `!stop` | Stop playback and disconnect from voice |
| `/queue` | `!queue` | View the current song queue |

**Supported sources:** YouTube (URLs and search queries), SoundCloud (direct track URLs).

---

## API Reference

All endpoints are served by the bot on port 8080. The dashboard's nginx proxy forwards `/api/*` and `/auth/*` requests there automatically.

Routes under `/api/` require a valid JWT session cookie (obtained via the OAuth2 flow). Routes under `/auth/` are public.

### Authentication

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/auth/discord` | Redirect to Discord OAuth2 login (accepts `guild_id` query param) |
| `GET` | `/auth/callback` | OAuth2 callback — exchanges code and issues a JWT session cookie |
| `GET` | `/auth/me` | Return the authenticated user `{id, username, avatar}` |
| `POST` | `/auth/logout` | Clear the session cookie |

### Guilds

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/guilds` | Return the list of guilds the bot is in `{guilds: [{id, name, icon}]}` |

### Queue

All queue routes require `guild_id` as a query parameter.

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/queue` | Fetch current track and upcoming queue `{current, tracks[]}` |
| `POST` | `/api/queue/add` | Add a track by URL `body: {url}` → `{added, track}` |
| `POST` | `/api/queue/skip` | Skip the current track → `{skipped, current, tracks[]}` |
| `POST` | `/api/queue/clear` | Clear the upcoming queue (keeps current track) → `{cleared}` |

### Playback

All playback routes require `guild_id` as a query parameter.

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/playback` | Get playback state `{state: "playing"\|"paused"\|"stopped", elapsed_seconds}` |
| `POST` | `/api/playback/pause` | Pause current playback → `{paused: true}` |
| `POST` | `/api/playback/resume` | Resume paused playback → `{resumed: true}` |
| `POST` | `/api/playback/stop` | Stop playback and disconnect from voice → `{stopped: true}` |

### Search

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/search` | Search YouTube: `?q={query}&limit={1-25}` → `{results[]}` |

---

## Screenshots

> Screenshots coming soon. Below are placeholder descriptions of the dashboard views:
>
> - **Login page** — Discord OAuth2 login button with bot branding
> - **Guild picker** — list of servers the bot is active in
> - **Dashboard** — now-playing bar, queue list, search bar, and playback controls (pause / resume / skip / stop)

---

## Docker Deployment

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin
- A configured `.env` file (copy from `.env.example`)

### Start all services

```bash
docker compose up -d --build
```

This builds and starts two containers:

| Container | Description | Exposed port |
| --- | --- | --- |
| `bot` | Discord bot + HTTP API | 8080 (internal only) |
| `dashboard` | React SPA served by nginx | 3000 |

### View logs

```bash
docker compose logs -f

# Tail a specific service
docker compose logs -f bot
docker compose logs -f dashboard
```

### Stop

```bash
docker compose down
```

### Update to a new version

```bash
git pull
docker compose up -d --build
```

> **Important:** Never commit `.env` to version control. It contains secrets.

---

## CI/CD Workflows

| Workflow | File | Trigger | Jobs |
| --- | --- | --- | --- |
| CI | [`ci.yml`](.github/workflows/ci.yml) | Push to `main` + PRs to `main` | `test-bot` (pytest + coverage + ruff check + ruff format), `lint-dashboard` (typecheck), `build-docker` (build both images) |
| Deploy | [`deploy.yml`](.github/workflows/deploy.yml) | Manual (`workflow_dispatch`) | Verifies CI passes on `main`, then SSH deploys to selected environment |

### CI checks (all must pass)

| Check | Command | Scope |
| --- | --- | --- |
| Pytest + coverage | `pytest --cov --cov-fail-under=70` | `tests/` (minimum 70% coverage) |
| Ruff lint | `ruff check bot/ tests/` | E, F, W rules |
| Ruff format | `ruff format --check bot/ tests/` | Consistent formatting |
| TypeScript | `npm run typecheck` | Dashboard types |
| Docker build | `docker build` | Bot + dashboard images |

### Deploy

Deployments are triggered manually from **GitHub Actions → Deploy → Run workflow**. Select the target environment (development or production). The workflow verifies CI is passing on `main` before deploying.

Required GitHub Actions secrets (configured per environment):

| Secret | Description |
| --- | --- |
| `DEV_HOST` / `PROD_HOST` | Server hostname or IP |
| `DEV_USER` / `PROD_USER` | SSH username |
| `DEV_SSH_KEY` / `PROD_SSH_KEY` | SSH private key |
| `DEV_DEPLOY_PATH` / `PROD_DEPLOY_PATH` | Path to docker-compose.yml on server |

---

## Project Structure

```
discord-music-bot/
├── bot/
│   ├── __main__.py          # Entry point — starts bot + API server
│   ├── bot.py               # Bot instantiation and cog loading
│   ├── api/
│   │   ├── server.py        # aiohttp app factory, health endpoint, startup
│   │   ├── auth.py          # Discord OAuth2 routes, JWT middleware, guild auth
│   │   ├── guilds.py        # GET /api/guilds
│   │   ├── player.py        # Queue and playback routes (uses MusicService)
│   │   └── search.py        # GET /api/search
│   ├── audio/
│   │   ├── resolver.py      # AudioResolver, AudioTrack, UnsupportedSourceError
│   │   ├── queue.py         # Queue class (per-guild track list)
│   │   └── voice.py         # VoiceManager (Discord voice connections)
│   ├── services/
│   │   └── music.py         # MusicService — shared playback state facade
│   └── cogs/
│       └── music.py         # Music commands cog (/play, /pause, /resume, …)
├── dashboard/
│   ├── src/
│   │   ├── App.tsx          # Auth state machine and root router
│   │   ├── api.ts           # Typed fetch helpers for all API routes
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── GuildPickerPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   └── components/
│   │       ├── PlayerBar.tsx
│   │       ├── PlaybackControls.tsx
│   │       ├── QueueView.tsx
│   │       ├── SearchBar.tsx
│   │       ├── Sidebar.tsx
│   │       └── AppShell.tsx
│   ├── Dockerfile           # Multi-stage build: Vite → nginx
│   └── nginx.conf           # Reverse-proxy /auth/* and /api/* to the bot
├── tests/
│   ├── unit/
│   │   ├── test_resolver.py
│   │   ├── test_queue.py
│   │   └── test_voice.py
│   └── integration/
│       ├── test_play_command.py
│       ├── test_queue_command.py
│       └── test_controls.py
├── .github/workflows/       # CI/CD workflow definitions
├── Dockerfile               # Bot container image
├── docker-compose.yml       # Orchestrates bot + dashboard
├── pyproject.toml           # Python project config and tool settings
└── .env.example             # Environment variable template
```

---

## Health Endpoints

| Endpoint | Description | Auth required |
| --- | --- | --- |
| `GET /health` (bot :8080) | Bot health + readiness status | No |
| `GET /health` (dashboard :3000) | Dashboard nginx health | No |
| `GET /health/bot` (dashboard :3000) | Bot health proxied through dashboard | No |

Both containers have Docker healthchecks. The dashboard waits for the bot to be healthy before starting.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide, branch naming conventions, PR checklist, and manual deployment instructions.

For AI coding agents (Claude, Copilot, Codex, Cursor, etc.), see [AGENTS.md](AGENTS.md) for architecture decisions, code patterns, testing conventions, and step-by-step guides for common tasks.
