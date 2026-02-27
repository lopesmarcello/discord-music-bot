# PRD: Discord Music Bot (Python)

## Introduction

A self-hosted Discord music bot written in Python that allows server members to stream audio from YouTube, Spotify, and SoundCloud into voice channels. The bot supports both slash commands and prefix commands, has a queue system, and is built using red/green TDD with unit and integration tests using a mocked Discord API.

## Goals

- Stream audio from YouTube, Spotify, and SoundCloud into Discord voice channels
- Provide playback controls: play, pause, resume, stop, skip
- Maintain a per-guild song queue with add/view/clear operations
- Support both slash commands (`/play`) and prefix commands (`!play`)
- Achieve >80% test coverage via unit + integration tests with mocked Discord API
- Ship a production-ready Dockerfile for self-hosted VPS deployment

## User Stories

---

### US-001: Project scaffold and CI setup

**Description:** As a developer, I need a clean project structure with dependencies, linting, and a test runner configured so I can begin TDD immediately.

**Acceptance Criteria:**

- [ ] `pyproject.toml` or `requirements.txt` includes: `discord.py`, `yt-dlp`, `spotipy`, `pytest`, `pytest-asyncio`, `pytest-cov`, `python-dotenv`
- [ ] `pytest` runs with zero errors on an empty test suite
- [ ] `README.md` documents how to run tests and the bot locally
- [ ] `.env.example` lists all required environment variables (`DISCORD_TOKEN`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `COMMAND_PREFIX`)

---

### US-002: Audio source resolver (RED/GREEN)

**Description:** As a developer, I need a source resolver that accepts a user query or URL and returns a playable audio stream URL so the bot can support multiple platforms uniformly.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests for `AudioResolver.resolve(query: str) -> AudioTrack` before implementation
- [ ] `resolve()` accepts a YouTube URL and returns an `AudioTrack` with `title`, `url`, `stream_url`, `duration`, `source` fields
- [ ] `resolve()` accepts a Spotify track URL, fetches metadata via Spotipy, and falls back to YouTube search for the stream URL
- [ ] `resolve()` accepts a SoundCloud URL and returns a valid `AudioTrack`
- [ ] `resolve()` accepts a plain search string and returns the top YouTube result
- [ ] `resolve()` raises `UnsupportedSourceError` for unrecognised URLs
- [ ] **GREEN:** All resolver unit tests pass with mocked `yt-dlp` and `spotipy` calls
- [ ] Coverage for `AudioResolver` is 100%

---

### US-003: Queue data structure (RED/GREEN)

**Description:** As a developer, I need an in-memory queue per guild so songs can be added, peeked at, skipped, and cleared without touching Discord or audio systems.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests for `Queue` class before implementation
- [ ] `Queue.add(track: AudioTrack)` appends a track
- [ ] `Queue.next()` removes and returns the front track; returns `None` if empty
- [ ] `Queue.peek()` returns the front track without removing it
- [ ] `Queue.clear()` empties the queue
- [ ] `Queue.list()` returns a copy of all tracks in order
- [ ] `Queue` is isolated per guild ID (keyed by `guild_id: int`)
- [ ] **GREEN:** All queue unit tests pass
- [ ] Coverage for `Queue` is 100%

---

### US-004: Voice connection manager (RED/GREEN)

**Description:** As a developer, I need a voice connection manager that joins/leaves voice channels and plays audio so playback logic is decoupled from command handling.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests using mocked `discord.VoiceClient` before implementation
- [ ] `VoiceManager.join(channel)` connects to a voice channel
- [ ] `VoiceManager.leave()` disconnects and clears state
- [ ] `VoiceManager.play(stream_url)` starts audio playback using FFmpeg via `discord.FFmpegPCMAudio`
- [ ] `VoiceManager.pause()` pauses currently playing audio
- [ ] `VoiceManager.resume()` resumes paused audio
- [ ] `VoiceManager.stop()` stops audio without disconnecting
- [ ] `VoiceManager.is_playing()` and `VoiceManager.is_paused()` return correct booleans
- [ ] After a track ends, `VoiceManager` automatically calls a registered `on_track_end` callback
- [ ] **GREEN:** All voice manager integration tests pass with mocked Discord voice client
- [ ] Coverage for `VoiceManager` is 100%

---

### US-005: `play` command (RED/GREEN)

**Description:** As a server member, I want to play a song by URL or search query so I can listen to music in a voice channel.

**Acceptance Criteria:**

- [ ] **RED:** Write failing integration tests with a mocked Discord context/interaction before implementation
- [ ] Slash command `/play <query>` is registered and callable
- [ ] Prefix command `!play <query>` works identically
- [ ] If the user is not in a voice channel, the bot replies with an error message and does not crash
- [ ] If the bot is not yet in a voice channel, it joins the user's channel automatically
- [ ] The resolved `AudioTrack` is added to the guild queue
- [ ] If nothing is currently playing, playback starts immediately
- [ ] If something is already playing, the track is queued and a confirmation message is sent: `"Added to queue: {title}"`
- [ ] **GREEN:** All play command tests pass
- [ ] Coverage for play command handler is ≥90%

---

### US-006: `pause` and `resume` commands (RED/GREEN)

**Description:** As a server member, I want to pause and resume playback so I can take breaks without losing my place.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests before implementation
- [ ] `/pause` and `!pause` pause currently playing audio; bot replies `"Paused."`
- [ ] `/resume` and `!resume` resume paused audio; bot replies `"Resumed."`
- [ ] If nothing is playing, pause replies with `"Nothing is currently playing."`
- [ ] If not paused, resume replies with `"Playback is not paused."`
- [ ] **GREEN:** All pause/resume tests pass

---

### US-007: `skip` command (RED/GREEN)

**Description:** As a server member, I want to skip the current song so I can move to the next track in the queue.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests before implementation
- [ ] `/skip` and `!skip` stop the current track and play the next one in the queue
- [ ] Bot replies with `"Skipped. Now playing: {next_title}"` if a next track exists
- [ ] Bot replies with `"Skipped. Queue is empty."` if the queue is now empty
- [ ] If nothing is playing, bot replies `"Nothing to skip."`
- [ ] **GREEN:** All skip tests pass

---

### US-008: `stop` command (RED/GREEN)

**Description:** As a server member, I want to stop playback and clear the queue so I can end the music session.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests before implementation
- [ ] `/stop` and `!stop` stop audio, clear the queue, and disconnect the bot from the voice channel
- [ ] Bot replies `"Stopped and disconnected."`
- [ ] If not in a voice channel, bot replies `"I'm not in a voice channel."`
- [ ] **GREEN:** All stop tests pass

---

### US-009: `queue` command (RED/GREEN)

**Description:** As a server member, I want to view the current song queue so I know what is coming up.

**Acceptance Criteria:**

- [ ] **RED:** Write failing tests before implementation
- [ ] `/queue` and `!queue` display an embed listing all queued tracks with position number, title, and duration
- [ ] The currently playing track is shown at the top labelled `"Now Playing"`
- [ ] If queue and current track are both empty, bot replies `"The queue is empty."`
- [ ] Queue embed shows a maximum of 10 tracks; if more exist, shows `"...and N more"`
- [ ] **GREEN:** All queue display tests pass

---

### US-010: Dockerfile and deployment config

**Description:** As a server admin, I need a Dockerfile so I can run the bot on a VPS without installing Python directly.

**Acceptance Criteria:**

- [ ] `Dockerfile` uses a slim Python base image (e.g., `python:3.12-slim`)
- [ ] FFmpeg is installed inside the image
- [ ] Bot starts with `CMD ["python", "-m", "bot"]` or equivalent
- [ ] `.dockerignore` excludes `.env`, `__pycache__`, `.git`
- [ ] `docker build` completes without errors
- [ ] `docker run` with a valid `.env` file starts the bot and connects to Discord
- [ ] `README.md` documents the full Docker deployment steps

---

## Functional Requirements

- **FR-1:** The bot must resolve audio from YouTube URLs, YouTube search queries, Spotify track URLs, and SoundCloud URLs.
- **FR-2:** Spotify track URLs must be resolved by fetching metadata via Spotipy, then searching YouTube for a matching stream.
- **FR-3:** Each Discord guild (server) must maintain its own independent queue.
- **FR-4:** All commands must be available as both slash commands and prefix commands (default prefix: `!`).
- **FR-5:** The command prefix must be configurable via the `COMMAND_PREFIX` environment variable.
- **FR-6:** The bot must automatically join the invoking user's voice channel when a play command is issued.
- **FR-7:** When a track finishes, the bot must automatically play the next track in the queue.
- **FR-8:** When the queue is exhausted and the current track ends, the bot must remain in the voice channel until `!stop` is issued.
- **FR-9:** All user-facing error messages must be non-crashing and sent as Discord replies.
- **FR-10:** All secrets (`DISCORD_TOKEN`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`) must be loaded from environment variables, never hardcoded.

## Non-Goals

- No volume control or equalizer settings
- No shuffle or repeat/loop mode
- No playlist support (YouTube playlists, Spotify playlists)
- No "now playing" progress bar or seek functionality
- No per-user or per-role permissions system
- No database persistence (queue is in-memory, resets on bot restart)
- No web dashboard or REST API
- No lyrics display

## Technical Considerations

- **Library:** `discord.py` (>=2.0) with `commands.Bot` for hybrid command support (slash + prefix)
- **Audio:** `yt-dlp` for extracting stream URLs; `FFmpegPCMAudio` for playback — FFmpeg must be available in PATH
- **Spotify:** `spotipy` with Client Credentials Flow (no user login required); used only for metadata, not streaming
- **SoundCloud:** handled via `yt-dlp` (it natively supports SoundCloud URLs)
- **Testing:** `pytest-asyncio` for async test support; `unittest.mock` / `AsyncMock` for mocking Discord objects; no real network calls in tests
- **TDD Cycle:** Write a failing test (RED) → implement the minimum code to pass (GREEN) → refactor → repeat. Each user story calls out the RED/GREEN steps explicitly.
- **Structure:**
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

## Success Metrics

- All user stories have passing tests before the implementation is considered complete
- `pytest --cov` reports ≥80% overall coverage
- Bot connects to Discord and plays audio within 3 seconds of a `/play` command on a VPS with a 1Gbps connection
- Zero unhandled exceptions during normal operation (play, skip, stop, queue)

## Open Questions

- Should the bot support multiple simultaneous voice channels within the same guild (e.g., different channels for different groups)? — Assumed **no** for MVP.
- Should the queue display use pagination (buttons) for servers with long queues, or is the 10-track cap sufficient? — Assumed **cap** is sufficient for now.
- Is there a preferred test fixture library (e.g., `pytest-mock` vs `unittest.mock`)? — Defaulting to `unittest.mock` with `AsyncMock`.
