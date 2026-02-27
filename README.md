# Discord Music Bot

A self-hosted Discord music bot written in Python that streams audio from YouTube, Spotify, and SoundCloud into voice channels. Supports both slash commands (`/play`) and prefix commands (`!play`).

## Features

- Stream audio from YouTube URLs, YouTube search queries, Spotify track URLs, and SoundCloud URLs
- Playback controls: play, pause, resume, stop, skip
- Per-guild song queue with add/view/clear operations
- Both slash commands (`/play`) and prefix commands (`!play`)
- Configurable command prefix via environment variable

## Requirements

- Python 3.11+
- FFmpeg (must be in PATH)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
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
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
COMMAND_PREFIX=!
```

#### Getting credentials

- **Discord token**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications), enable "Message Content Intent" under Bot settings
- **Spotify credentials**: Create an app at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) using Client Credentials flow

### 4. Run the bot

```bash
python -m bot
```

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

- [Docker](https://docs.docker.com/get-docker/) installed on your VPS or local machine
- A configured `.env` file (copy from `.env.example` and fill in credentials)

### Build the image

```bash
docker build -t discord-music-bot .
```

### Run the container

```bash
docker run --env-file .env discord-music-bot
```

### Run in the background (detached)

```bash
docker run -d --name music-bot --restart unless-stopped --env-file .env discord-music-bot
```

### View logs

```bash
docker logs -f music-bot
```

### Stop / restart the bot

```bash
docker stop music-bot
docker start music-bot
```

### Update to a new version

```bash
docker stop music-bot
docker rm music-bot
docker build -t discord-music-bot .
docker run -d --name music-bot --restart unless-stopped --env-file .env discord-music-bot
```

**Note:** Make sure your `.env` file is configured with valid credentials before running. Never commit `.env` to version control.

## Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `/play <query>` | `!play <query>` | Play a song by URL or search query |
| `/pause` | `!pause` | Pause currently playing audio |
| `/resume` | `!resume` | Resume paused audio |
| `/skip` | `!skip` | Skip to the next song |
| `/stop` | `!stop` | Stop playback and disconnect |
| `/queue` | `!queue` | View the current song queue |

## Supported Sources

- **YouTube**: Direct URLs or search queries
- **Spotify**: Track URLs (metadata fetched, streamed via YouTube)
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
tests/
  unit/
    test_resolver.py
    test_queue.py
    test_voice.py
  integration/
    test_play_command.py
    test_queue_command.py
    test_controls.py
Dockerfile
.env.example
pyproject.toml
```
