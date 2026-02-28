# PRD: Web Dashboard for Discord Music Bot

## Introduction

Add a web-based dashboard that lets Discord guild members control the music bot from a browser. Users authenticate via Discord OAuth2, ensuring only members of the server can access the controls. The dashboard displays the live song queue, provides a YouTube search bar to add tracks, and exposes full playback controls (pause, resume, skip, stop, remove tracks, clear queue).

The dashboard is a new React (TypeScript) frontend container served by nginx, communicating with an HTTP API embedded in the existing bot container.

---

## Goals

- Let any guild member control the music bot without opening Discord
- Authenticate users via Discord OAuth2 so only guild members can access
- Display the current queue in real time (polling)
- Allow searching YouTube and adding tracks to the queue
- Expose all playback controls available via slash commands
- Ship as a new service in the existing Docker Compose setup with minimal changes to the bot

---

## User Stories

### US-001: Embed HTTP API server in the bot
**Description:** As a developer, I need the bot to expose a REST API so the dashboard can read queue state and issue commands.

**Acceptance Criteria:**
- [x] An `aiohttp` web server starts alongside the bot's event loop on a configurable port (default `8080`)
- [x] Server port is configurable via `API_PORT` env variable
- [x] Server only binds to `0.0.0.0` so Docker networking works
- [x] The bot starts and passes existing tests with the API server running
- [x] Typecheck/lint passes

### US-002: Implement Discord OAuth2 authentication in the API
**Description:** As a developer, I need the API to authenticate users via Discord OAuth2 so only guild members can access the dashboard.

**Acceptance Criteria:**
- [ ] `GET /auth/discord?guild_id={id}` redirects to Discord OAuth2 authorization URL
- [ ] `GET /auth/callback` exchanges the code for a Discord access token, fetches the user's guilds, and verifies membership in the requested guild
- [ ] On success, returns a signed JWT session token (stored as an HTTP-only cookie)
- [ ] On failure (not in guild, invalid code), redirects to dashboard with an error query param
- [ ] `GET /auth/me` returns `{id, username, avatar}` for the authenticated user, or 401
- [ ] `POST /auth/logout` clears the session cookie
- [ ] All API routes except `/auth/*` require a valid JWT; return 401 otherwise
- [ ] Required env variables documented: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`, `JWT_SECRET`
- [ ] Typecheck/lint passes

### US-003: Implement queue and playback API endpoints
**Description:** As a developer, I need REST endpoints that expose the bot's queue state and accept playback commands for a given guild.

**Acceptance Criteria:**
- [ ] `GET /api/guilds/{guild_id}/queue` returns `{now_playing: Track|null, queue: Track[], is_paused: bool}`
  - `Track` shape: `{title: string, url: string, duration: string, thumbnail: string|null, requested_by: string}`
- [ ] `POST /api/guilds/{guild_id}/queue` body `{query: string}` — searches YouTube, enqueues the top result, returns the added `Track`; if bot is not in a voice channel, it joins the requester's channel (if discoverable) or returns a 409 with message `"Bot is not in a voice channel"`
- [ ] `DELETE /api/guilds/{guild_id}/queue` — clears the entire queue
- [ ] `DELETE /api/guilds/{guild_id}/queue/{index}` — removes track at zero-based index; returns 404 if index out of range
- [ ] `POST /api/guilds/{guild_id}/playback/pause` — pauses; returns 409 if already paused or nothing playing
- [ ] `POST /api/guilds/{guild_id}/playback/resume` — resumes; returns 409 if not paused
- [ ] `POST /api/guilds/{guild_id}/playback/skip` — skips current track
- [ ] `POST /api/guilds/{guild_id}/playback/stop` — stops and disconnects bot
- [ ] All endpoints return 404 if guild_id is not found/bot not in guild
- [ ] Typecheck/lint passes

### US-004: Implement YouTube search API endpoint
**Description:** As a developer, I need a search endpoint so the frontend can show search suggestions before the user commits to adding a track.

**Acceptance Criteria:**
- [ ] `GET /api/search?q={query}` returns up to 5 YouTube results: `[{title, url, duration, thumbnail, channel}]`
- [ ] Uses `yt-dlp` (already a dependency) with `ytsearch5:` prefix to fetch results without downloading
- [ ] Returns empty array (not an error) if no results found
- [ ] Typecheck/lint passes

### US-005: Add dashboard service to Docker Compose
**Description:** As a developer, I need the React app and API to be wired up in Docker Compose so the full stack runs with `docker compose up`.

**Acceptance Criteria:**
- [ ] New `dashboard` service in `docker-compose.yml` builds from `dashboard/Dockerfile`
- [ ] `dashboard` service exposes port `3000` (host) → `80` (container, nginx)
- [ ] nginx reverse-proxies `/auth/*` and `/api/*` to the `bot` service on port `8080`
- [ ] `bot` service exposes port `8080` internally (not necessarily to host)
- [ ] All required env variables (`DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`, `JWT_SECRET`) added to `.env.example` with placeholder values
- [ ] `docker compose up --build` starts both services without errors
- [ ] Typecheck/lint passes

### US-006: Build React app skeleton with login page
**Description:** As a guild member, I want to see a login page when I'm not authenticated so I can connect my Discord account.

**Acceptance Criteria:**
- [ ] React + TypeScript project scaffolded in `dashboard/` using Vite
- [ ] Login page shows the bot name/logo, a "Login with Discord" button, and a guild ID input field (pre-filled from URL param `?guild=`)
- [ ] Clicking the button redirects to `/auth/discord?guild_id={id}`
- [ ] If `?error=not_in_guild` is present in the URL, show an error message: "You are not a member of this server."
- [ ] Unauthenticated users on any route are redirected to the login page
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

### US-007: Build main dashboard queue view
**Description:** As a guild member, I want to see the current queue and now-playing track when I open the dashboard.

**Acceptance Criteria:**
- [ ] Header shows the authenticated user's Discord avatar and username with a logout button
- [ ] "Now Playing" section shows current track's title, channel, duration, and thumbnail (or empty state if nothing is playing)
- [ ] Queue list shows all upcoming tracks in order: position number, thumbnail, title, channel, duration, and a remove (×) button per track
- [ ] Empty queue shows message: "The queue is empty. Search for a song to get started."
- [ ] Queue data is fetched from `GET /api/guilds/{guild_id}/queue` and re-polled every 5 seconds
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

### US-008: Build YouTube search bar and add-to-queue flow
**Description:** As a guild member, I want to search YouTube and add a song to the queue without leaving the dashboard.

**Acceptance Criteria:**
- [ ] Search input is always visible at the top of the dashboard (above the queue)
- [ ] Typing 3+ characters triggers a debounced call (300 ms) to `GET /api/search?q=`
- [ ] Dropdown shows up to 5 results: thumbnail, title, channel, duration
- [ ] Clicking a result calls `POST /api/guilds/{guild_id}/queue` with the track URL and closes the dropdown
- [ ] A loading spinner is shown while the add request is in flight; the queue refreshes immediately after success
- [ ] If the bot is not in a voice channel (409), show inline error: "The bot is not in a voice channel."
- [ ] Pressing Escape closes the dropdown; clicking outside also closes it
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

### US-009: Build playback controls bar
**Description:** As a guild member, I want playback controls on the dashboard so I can pause, skip, or stop the bot.

**Acceptance Criteria:**
- [ ] Persistent controls bar at the bottom of the dashboard (or below "Now Playing")
- [ ] Buttons: Pause/Resume (toggle based on `is_paused`), Skip, Stop, Clear Queue
- [ ] Each button is disabled when no track is playing (except Clear Queue, which is also disabled when queue is empty)
- [ ] Clicking any button calls the corresponding API endpoint and refreshes the queue
- [ ] Buttons show a brief loading state while the request is in flight
- [ ] Failed requests show a toast/snackbar error message
- [ ] Typecheck/lint passes
- [ ] Verify in browser using dev-browser skill

---

## Functional Requirements

- **FR-1:** The bot must start an `aiohttp` HTTP server in the same asyncio event loop on `API_PORT` (default `8080`)
- **FR-2:** All API routes except `/auth/*` must require a valid JWT session; return `401` for missing or invalid tokens
- **FR-3:** Discord OAuth2 must verify the authenticated user is a member of the requested guild before issuing a session
- **FR-4:** `GET /api/guilds/{guild_id}/queue` must reflect live in-memory queue state with no database
- **FR-5:** `POST /api/guilds/{guild_id}/queue` must use yt-dlp to resolve the track and enqueue it, consistent with how `/play` works today
- **FR-6:** `GET /api/search?q=` must return up to 5 YouTube results using yt-dlp's `ytsearch5:` mode
- **FR-7:** The React dashboard must poll the queue endpoint every 5 seconds to reflect changes made by other users (via Discord or dashboard)
- **FR-8:** The dashboard must be served by nginx, which reverse-proxies API calls to the bot container
- **FR-9:** Remove-track and clear-queue actions must ask for confirmation before executing
- **FR-10:** The guild ID must be passed to the dashboard via URL (`?guild=`) or persisted in `localStorage` after first login

---

## Non-Goals

- No WebSocket / push-based real-time updates (polling is sufficient for v1)
- No per-user permission tiers (any guild member can use all controls)
- No SoundCloud search (SoundCloud direct URLs still work when pasted, but the search bar only queries YouTube)
- No mobile-native app; responsive web only
- No user history or "who added this" attribution beyond what the bot already tracks
- No multi-guild switcher UI (guild is fixed per dashboard URL/session)
- No dark/light theme toggle

---

## Design Considerations

- Keep the UI minimal and functional: dark theme (fits Discord aesthetic), simple list-based queue
- Reuse the same color tokens Discord uses (`#5865F2` blurple for primary actions)
- The nginx container serves the pre-built React bundle — no Node.js runtime in production

---

## Technical Considerations

- **aiohttp** should be added as a dependency in `pyproject.toml`; it is compatible with `discord.py`'s asyncio loop
- **PyJWT** for issuing/verifying session tokens; add to `pyproject.toml`
- The bot's in-memory `Queue` and `VoiceManager` objects must be accessible from the API handlers — pass them via a shared app context
- yt-dlp is already a dependency; use `extract_info` with `download=False` and `ytsearch5:` prefix for search
- `DISCORD_REDIRECT_URI` must match exactly what is registered in the Discord Developer Portal (e.g., `http://localhost:3000/auth/callback`)
- The React app uses `VITE_GUILD_ID` as an optional env var to pre-fill the guild field

---

## Success Metrics

- Any guild member can open the dashboard, log in with Discord, and add a song to the queue within 60 seconds
- Playback controls on the dashboard produce the same result as the equivalent slash commands in Discord
- Queue view is never more than 10 seconds out of date (5-second poll + render time)
- `docker compose up --build` is the only command needed to run the full stack

---

## Open Questions

- Should the bot auto-join a voice channel when a song is added via the dashboard, and if so, which channel? (Current assumption: return 409 and show an error — the user must use `/play` in Discord first to put the bot in a channel)
- Should the login page accept any guild ID (open), or should the bot expose a list of guilds it's in so the user can pick from a dropdown?
- Is a guild ID input field on the login page acceptable UX, or should the dashboard URL encode the guild (e.g., `/guild/123456789`)?
