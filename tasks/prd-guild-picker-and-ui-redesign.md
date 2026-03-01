# PRD: Guild Picker Fallback & Music App UI Redesign

## Introduction

The dashboard currently shows a dead-end "No guild selected" message when no `?guild=` parameter exists in the URL. This feature replaces that dead end with a guild picker page that lists every server the bot has joined, so any user can reach the dashboard without needing a pre-built link.

Alongside that, the entire frontend receives a full redesign modelled on Spotify / Apple Music / Deezer: a collapsible left sidebar, a persistent bottom player bar with thumbnail and progress, and a colour palette in tribute to Claude (dark charcoal + orange).

---

## Goals

- Eliminate the broken "no guild" state — any authenticated user lands somewhere useful.
- Let users switch guilds from within the UI without constructing a URL by hand.
- Deliver a music-streaming-app visual experience (Spotify-style layout, bottom player bar).
- Apply a consistent Claude-tribute colour scheme: dark charcoal backgrounds + orange accent.
- Keep all existing playback, queue, and search functionality intact.

---

## Colour Palette (Design Reference)

| Token | Value | Usage |
|---|---|---|
| `--bg-base` | `#111111` | Page / sidebar background |
| `--bg-surface` | `#1E1E1E` | Cards, panels |
| `--bg-elevated` | `#2A2A2A` | Hover states, inputs |
| `--accent` | `#E8671B` | Primary CTA, active nav, progress fill |
| `--accent-hover` | `#F07A35` | Hovered accent elements |
| `--text-primary` | `#FFFFFF` | Headings, track titles |
| `--text-secondary` | `rgba(255,255,255,0.55)` | Subtitles, metadata |
| `--text-muted` | `rgba(255,255,255,0.25)` | Disabled, track index numbers |
| `--border` | `rgba(255,255,255,0.08)` | Dividers, card borders |
| `--sidebar-bg` | `#0D0D0D` | Sidebar panel |
| `--player-bg` | `#161616` | Bottom player bar |

---

## Layout Reference

```
┌──────────────────────────────────────────────────────┐
│  SIDEBAR (collapsible, 220px ↔ 64px)                 │
│  ┌──────┬───────────────────────────────────────┐   │
│  │ logo │    MAIN CONTENT AREA                  │   │
│  │ nav  │    [page header]                      │   │
│  │ items│    [search bar]                       │   │
│  │      │    [queue list]                       │   │
│  └──────┴───────────────────────────────────────┘   │
├──────────────────────────────────────────────────────┤
│  BOTTOM PLAYER BAR (fixed, 80px tall)                │
│  [thumbnail 56px] [title / artist] [▶ ⏭ ⏹] [━━━] │
└──────────────────────────────────────────────────────┘
```

---

## User Stories

### US-001: Add `/api/guilds` endpoint
**Description:** As a developer, I need an API endpoint that returns the list of guilds the bot is currently a member of so the frontend can render the guild picker.

**Acceptance Criteria:**
- [ ] `GET /api/guilds` returns JSON: `{ "guilds": [{ "id": "...", "name": "...", "icon": "..." | null }] }`
- [ ] Route is protected by the existing JWT middleware (must be authenticated)
- [ ] `icon` is the Discord icon hash string (not a full URL); frontend builds the CDN URL
- [ ] Returns empty list `[]` if bot has no guilds
- [ ] Add `fetchGuilds()` to `dashboard/src/api.ts` with type `Guild { id, name, icon: string | null }`
- [ ] Typecheck passes

### US-002: Add `thumbnail` field to `AudioTrack` model and API responses
**Description:** As a developer, I need the current-track data to include a thumbnail URL so the bottom player bar can display album art.

**Acceptance Criteria:**
- [ ] `AudioTrack` dataclass gains field `thumbnail: str` (empty string when unavailable)
- [ ] `_make_track` in `resolver.py` populates `thumbnail` from yt-dlp `info["thumbnail"]` (fallback `""`)
- [ ] `/api/queue` response includes `"thumbnail"` on both `current` and `tracks[]` items
- [ ] `Track` interface in `api.ts` gains `thumbnail: string`
- [ ] Typecheck passes

### US-003: Add `elapsed_seconds` to `/api/playback` response
**Description:** As a developer, I need to know how many seconds into the current track we are so the frontend can render an accurate progress bar.

**Acceptance Criteria:**
- [ ] `Music` cog records `_started_at: dict[int, float]` — a unix timestamp per guild when a track starts playing, reset to `None` when stopped/paused
- [ ] When paused, elapsed is frozen (store offset); when resumed, timestamp resets accounting for offset
- [ ] `/api/playback` response gains `"elapsed_seconds": float | None` (None when stopped)
- [ ] `fetchPlayback` return type in `api.ts` gains `elapsedSeconds: number | null`
- [ ] Typecheck passes

### US-004: Set up global design tokens
**Description:** As a developer, I need CSS custom properties (design tokens) defined globally so all components share the same colours and typography without inline duplication.

**Acceptance Criteria:**
- [ ] `index.css` defines all tokens from the colour palette table above as `--` CSS variables on `:root`
- [ ] Global resets applied: `box-sizing: border-box`, `margin: 0`, `font-family` set to system stack
- [ ] `body` background set to `var(--bg-base)`, colour to `var(--text-primary)`
- [ ] Tokens are used (not hardcoded values) in at least one component to confirm wiring works
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-005: Build `GuildPickerPage` component
**Description:** As an authenticated user, I want to see a list of servers the bot is in when I open the dashboard without a guild link, so I can pick where to go.

**Acceptance Criteria:**
- [ ] `src/pages/GuildPickerPage.tsx` created
- [ ] Calls `fetchGuilds()` on mount; shows a loading skeleton while fetching
- [ ] Renders a grid of guild cards — each card shows the guild icon (or a placeholder initial letter circle) and guild name
- [ ] Clicking a guild card navigates to `/?guild={id}` (sets `window.location.search`)
- [ ] Empty state shown if `guilds` list is empty: "The bot is not in any servers yet."
- [ ] Error state shown if fetch fails: "Could not load servers. Please try again."
- [ ] Guild card uses orange accent on hover (border and icon glow)
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-006: Update `App.tsx` routing for guild picker flow
**Description:** As a user, I want the app to automatically route me to the guild picker when I'm logged in but haven't selected a guild, so I never see an error screen.

**Acceptance Criteria:**
- [ ] When `auth.status === 'authenticated'` and `guildId` is `undefined`, render `<GuildPickerPage>` instead of the old "no guild" state
- [ ] When `auth.status === 'authenticated'` and `guildId` is defined, render `<DashboardPage>` (existing behaviour)
- [ ] `GuildPickerPage` receives the `user` and `onLogout` props so the header/sidebar can render
- [ ] Typecheck passes

### US-007: Build collapsible `Sidebar` component
**Description:** As a user, I want a left sidebar that I can collapse to icon-only mode so I have more screen space while still being able to navigate.

**Acceptance Criteria:**
- [ ] `src/components/Sidebar.tsx` created
- [ ] Expanded state (220 px wide): shows bot logo/wordmark at top, nav items with icon + label, current guild name and icon at bottom
- [ ] Collapsed state (64 px wide): shows icons only, no labels; guild name hidden
- [ ] Toggle button (chevron icon) at the bottom of the sidebar switches between states
- [ ] Collapsed/expanded state is stored in `localStorage` and restored on reload
- [ ] Nav items: **Queue** (home icon), **Search** (magnifier icon) — clicking sets active view in `DashboardPage`
- [ ] Active nav item highlighted with orange left-border and slightly lighter background
- [ ] Sidebar background uses `var(--sidebar-bg)`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-008: Build `AppShell` layout component
**Description:** As a developer, I need a layout wrapper that positions the sidebar, main content area, and bottom player bar correctly so all pages share the same chrome.

**Acceptance Criteria:**
- [ ] `src/components/AppShell.tsx` created; accepts `sidebar`, `children`, and `playerBar` render props/slots
- [ ] Uses CSS Grid: `[sidebar] [main]` columns with `sidebar` width driven by collapsed state via a CSS variable or class
- [ ] Bottom player bar is `position: fixed; bottom: 0; left: 0; right: 0; height: 80px`
- [ ] Main content area has `padding-bottom: 96px` to avoid content hiding behind the player bar
- [ ] Header inside main area shows: current guild name + icon on left; user avatar + username + logout on right
- [ ] `DashboardPage` and `GuildPickerPage` both render inside `AppShell`
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-009: Build `PlayerBar` bottom component
**Description:** As a user, I want a persistent bottom bar showing what's currently playing, with thumbnail, title, progress, and playback controls, so I always know the playback state and can control it from anywhere.

**Acceptance Criteria:**
- [ ] `src/components/PlayerBar.tsx` created
- [ ] Left section (flex-shrink 0): 56×56 px thumbnail (`<img>`) with fallback grey square when `thumbnail` is empty; track title and source label next to it
- [ ] Centre section: Play/Pause button, Skip button, Stop button — styled as circular icon buttons
- [ ] Right section: progress bar showing `elapsed / duration` as a filled orange bar; elapsed and total time labels (e.g., `1:23 / 3:45`)
- [ ] Progress bar updates every second via a `setInterval` when state is `'playing'`
- [ ] When state is `'stopped'`, the bar shows "Nothing playing" placeholder text and controls are dimmed
- [ ] Player bar background: `var(--player-bg)` with a `1px solid var(--border)` top border
- [ ] Polls `/api/playback` and `/api/queue` every 5 s to stay in sync; does not replace the local second-tick timer
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-010: Redesign `QueueView` component
**Description:** As a user, I want the queue list to look like a Spotify track list — clean rows with index, thumbnail, title, and duration — styled with the new design tokens.

**Acceptance Criteria:**
- [ ] Track rows use `var(--bg-surface)` background with `var(--border)` border on hover
- [ ] "Now Playing" track row has an orange left accent bar (`border-left: 3px solid var(--accent)`) and slightly elevated background
- [ ] Each row shows: index number (muted), 40×40 px thumbnail (or letter placeholder), title (primary), duration (secondary right-aligned)
- [ ] Skip button replaced by a skip icon (⏭) inline in the now-playing row, not a separate button below
- [ ] "Clear Queue" button styled as a small outlined button using `var(--accent)` border/text colour
- [ ] Empty state message: "Queue is empty" in muted text, centred
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-011: Redesign `SearchBar` component
**Description:** As a user, I want the search experience to look like a music app — full-width search input, results with thumbnails, and an "Add" button per result — styled with the new design tokens.

**Acceptance Criteria:**
- [ ] Search input is full-width with rounded corners, `var(--bg-elevated)` background, and orange focus ring (`outline: 2px solid var(--accent)`)
- [ ] Search button uses `var(--accent)` background
- [ ] Each result row shows: 48×48 thumbnail, title, duration, and an "+ Add" button on the right
- [ ] "+ Add" button uses `var(--accent)` outline style; transitions to filled orange while adding
- [ ] After adding, the row shows a brief "Added ✓" confirmation before reverting
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-012: Redesign `LoginPage` component
**Description:** As a user, I want the login page to match the new design — dark charcoal background, Claude orange accents — so it feels like part of the same app.

**Acceptance Criteria:**
- [ ] Background: `var(--bg-base)` solid (no gradient)
- [ ] Card: `var(--bg-surface)` with `var(--border)` border, 16 px border-radius
- [ ] App logo or wordmark at top of card
- [ ] "Login with Discord" button: `var(--accent)` background, white text, Discord icon on left
- [ ] Error banner: red tint background, same style as before but using design token colours
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

---

## Functional Requirements

- **FR-1:** `GET /api/guilds` returns `{ guilds: Array<{ id: string, name: string, icon: string | null }> }` drawn from `bot.guilds`; requires JWT auth.
- **FR-2:** `AudioTrack.thumbnail` stores the first thumbnail URL returned by yt-dlp (empty string when absent).
- **FR-3:** `/api/playback` response includes `elapsed_seconds: float | null`; the Music cog tracks playback start time per guild.
- **FR-4:** When the user is authenticated and no `?guild=` param is present, the app renders `GuildPickerPage` (not an error message).
- **FR-5:** Clicking a guild in the picker sets `?guild={id}` in the URL and transitions to `DashboardPage`.
- **FR-6:** The sidebar collapses to 64 px and expands to 220 px; state persists in `localStorage`.
- **FR-7:** The bottom player bar is always visible when authenticated (even in GuildPickerPage; it shows "Nothing playing" when no guild is active).
- **FR-8:** The progress bar in the player bar ticks every 1 second client-side using `elapsed_seconds` as the baseline.
- **FR-9:** All colour values in components use CSS custom properties from `index.css`, not hardcoded hex values.

---

## Non-Goals

- No user-level guild filtering — all authenticated users see all guilds the bot is in.
- No drag-to-reorder in the queue.
- No volume control slider.
- No lyrics display.
- No mobile / responsive breakpoints (desktop-first for now).
- No dark/light theme toggle.
- No guild-specific settings or permissions UI.

---

## Design Considerations

- Guild icons from Discord CDN: `https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png?size=64`. When `icon` is null, render a circle with the first letter of the guild name in `var(--accent)`.
- User avatars from Discord CDN: `https://cdn.discordapp.com/avatars/{user_id}/{hash}.png?size=32`.
- Progress bar: simple `<div>` with `width: (elapsed/duration * 100)%` filled in `var(--accent)`, no native `<input type="range">` needed.
- Sidebar nav icons can be Unicode symbols or inline SVGs — keep it simple.
- The `PlayerBar` should receive `guildId` as a prop (can be `undefined` when on the picker page) and skip polling when undefined.

---

## Technical Considerations

- `bot.guilds` is available on the `discord.ext.commands.Bot` instance; access via `request.app["bot"].guilds` in the route handler.
- Track elapsed time: store `_play_started_at: dict[int, float]` in the Music cog using `time.time()`. When paused, compute and store `_elapsed_offset: dict[int, float]`; when resumed, subtract offset from new `time.time()` baseline. Elapsed = `time.time() - _play_started_at[guild_id] + _elapsed_offset.get(guild_id, 0)`.
- The `AppShell` sidebar width transition should use `CSS transition: width 0.25s ease` for smooth animation.
- The `DashboardPage` active view (`'queue' | 'search'`) should be lifted up to `App.tsx` or kept in `DashboardPage` state and passed down to `Sidebar` as `activeView` + `onViewChange`.

---

## Success Metrics

- A user with no guild link in the URL can reach the correct dashboard in ≤ 2 clicks after login.
- The current track title and thumbnail appear in the player bar within 5 seconds of playback starting.
- The progress bar stays within ±2 seconds of actual playback position across a 3-minute track.
- All existing tests pass with no regressions.

---

## Open Questions

- Should the guild picker also be accessible from within the dashboard (e.g., a "Switch Server" link in the sidebar), or only on initial load? Currently scoped to initial load only.
- Should the sidebar show a "Disconnect bot" option per guild, or is that out of scope? Currently out of scope.
- What happens when `duration` is `null` (live streams)? The progress bar should show elapsed time only, with no total and no percentage fill.
