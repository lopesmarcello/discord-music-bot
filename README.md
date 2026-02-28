# Discord Music Bot

A self-hosted Discord music bot written in Python that streams audio from YouTube and SoundCloud into voice channels. Supports both slash commands (`/play`) and prefix commands (`!play`).

## Features

- Stream audio from YouTube URLs, YouTube search queries, and SoundCloud URLs
- Playback controls: play, pause, resume, stop, skip
- Per-guild song queue with add/view/clear operations
- Slash commands (`/play`)

## Requirements

- Python 3.11+
- FFmpeg (must be in PATH)

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

*command prefix may not work sometimes, still workingo on it
```

#### Getting credentials

- **Discord token**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications), enable "Message Content Intent" under Bot settings

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

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin installed on your VPS or local machine
- A configured `.env` file (copy from `.env.example` and fill in credentials)

### Start the bot

```bash
docker compose up -d --build
```

This builds the image and starts the container in the background with `restart: unless-stopped`.

### View logs

```bash
docker compose logs -f
```

### Stop the bot

```bash
docker compose down
```

### Update to a new version

```bash
docker compose up -d --build
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

- **YouTube**: Direct URLs
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
