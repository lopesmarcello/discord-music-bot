# Discord Music Bot

A self-hosted Discord music bot written in Python that streams audio from YouTube and SoundCloud into voice channels. Supports both slash commands (`/play`) and prefix commands (`!play`), plus a browser-based web dashboard for queue management and playback control.

## Features

- Stream audio from YouTube URLs, YouTube search queries, and SoundCloud URLs
- Playback controls: play, pause, resume, stop, skip
- Per-guild song queue with add/view/clear operations
- Slash commands (`/play`) and prefix commands (`!play`)
- Web dashboard: browser-based queue view, YouTube search, and playback controls (authenticated via Discord OAuth2)

## Requirements

- Python 3.11+
- FFmpeg (must be in PATH)
- Node.js 18+ (only needed to build the dashboard outside Docker)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/lopesmarcello/discord-music-bot
cd discord-music-bot
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
DISCORD_TOKEN=your_discord_bot_token
COMMAND_PREFIX=!

# HTTP API port (default: 8080)
API_PORT=8080

# Discord OAuth2 — required for the web dashboard
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback

# Secret used to sign JWT session cookies (use a long random string)
JWT_SECRET=your_jwt_secret

# URL the bot redirects to after OAuth2 (default: http://localhost:3000)
DASHBOARD_URL=http://localhost:3000
```

#### Getting credentials

- **Discord token**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications), enable "Message Content Intent" under Bot settings.
- **Client ID / Secret**: In the same application, go to **OAuth2 → General** and copy the Client ID and Client Secret.
- **Redirect URI**: Add `http://localhost:3000/auth/callback` (or your production URL) to the list of allowed redirects in **OAuth2 → Redirects**.
- **JWT secret**: Any long random string, e.g. `openssl rand -hex 32`.

### 4. Run the bot

```bash
python -m bot
```

This starts both the Discord bot and the HTTP API server (default port 8080).

### 5. Access the dashboard

Open `http://localhost:3000?guild=YOUR_GUILD_ID` in a browser. You will be redirected to Discord to log in; after authorising, the dashboard loads for the specified guild.

> **Note:** The dashboard is only served automatically when using Docker Compose (see below). To serve it locally without Docker, build it (`npm install && npm run build` inside `dashboard/`) and point a static file server at `dashboard/dist/`.

## Web Dashboard

The dashboard is a React + Vite single-page app served by nginx. It communicates with the bot's HTTP API and authenticates users via Discord OAuth2 (JWT session cookie).

### API routes (bot, port 8080)

| Route | Description |
| --- | --- |
| `GET /auth/discord` | Redirect to Discord OAuth2 login |
| `GET /auth/callback` | OAuth2 callback — issues a JWT cookie |
| `GET /auth/me` | Return the authenticated user |
| `POST /auth/logout` | Clear the session cookie |
| `GET /api/queue` | Fetch current queue for a guild |
| `POST /api/queue/add` | Add a track by URL |
| `POST /api/queue/skip` | Skip the current track |
| `POST /api/queue/clear` | Clear the upcoming queue |
| `GET /api/search` | Search YouTube |
| `GET /api/playback` | Get playback state |
| `POST /api/playback/pause` | Pause |
| `POST /api/playback/resume` | Resume |
| `POST /api/playback/stop` | Stop and disconnect |

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=bot --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

## Docker Deployment

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin installed on your VPS or local machine
- A configured `.env` file (copy from `.env.example` and fill in credentials)

### Start everything

```bash
docker compose up -d --build
```

This builds and starts two containers:

| Container | Description | Port |
| --- | --- | --- |
| `bot` | Discord bot + HTTP API | 8080 (internal) |
| `dashboard` | React SPA served by nginx | 3000 |

### View logs

```bash
docker compose logs -f
```

### Stop

```bash
docker compose down
```

### Update to a new version

```bash
docker compose up -d --build
```

**Note:** Make sure your `.env` file is configured with valid credentials before running. Never commit `.env` to version control.

## Commands

| Command         | Alias           | Description                        |
| --------------- | --------------- | ---------------------------------- |
| `/play <query>` | `!play <query>` | Play a song by URL or search query |
| `/pause`        | `!pause`        | Pause currently playing audio      |
| `/resume`       | `!resume`       | Resume paused audio                |
| `/skip`         | `!skip`         | Skip to the next song              |
| `/stop`         | `!stop`         | Stop playback and disconnect       |
| `/queue`        | `!queue`        | View the current song queue        |

## Supported Sources

- **YouTube**: Direct URLs and search queries
- **SoundCloud**: Direct track URLs

## Project Structure

```
bot/
  __main__.py        # Entry point
  bot.py             # Bot instantiation and cog loading
  cogs/
    music.py         # All music commands (Cog)
  audio/
    resolver.py      # AudioResolver, AudioTrack, UnsupportedSourceError
    queue.py         # Queue class
    voice.py         # VoiceManager class
  api/
    server.py        # aiohttp app factory and startup helper
    auth.py          # Discord OAuth2 routes and JWT middleware
    player.py        # Playback control routes (/api/playback/*)
    search.py        # YouTube search route (/api/search)
dashboard/
  src/
    App.tsx          # Auth state machine and root router
    api.ts           # Typed fetch helpers for all API routes
    pages/
      LoginPage.tsx  # Unauthenticated landing page
      DashboardPage.tsx  # Main dashboard layout
    components/
      QueueView.tsx      # Current track + upcoming queue list
      SearchBar.tsx      # YouTube search + add-to-queue flow
      PlaybackControls.tsx  # Pause / resume / skip / stop buttons
  Dockerfile         # Multi-stage build: Vite → nginx
  nginx.conf         # Reverse-proxy /auth/* and /api/* to the bot
tests/
  unit/
    test_resolver.py
    test_queue.py
    test_voice.py
  integration/
    test_play_command.py
    test_queue_command.py
    test_controls.py
Dockerfile           # Bot image
docker-compose.yml   # Orchestrates bot + dashboard
.env.example
pyproject.toml
```
