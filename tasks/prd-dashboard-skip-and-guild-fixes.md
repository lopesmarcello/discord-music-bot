# PRD: Dashboard Skip Clearing & Guild Selector Fixes

## Introduction

Two production regressions have returned on the VPS deployment:

1. **Dashboard clearing on skip** — when a song is skipped, the dashboard briefly goes blank (queue clears, player bar shows "Nothing playing") even though the Discord bot continues playing the next track normally. This is caused by a timing race: `PlayerBar` discards the skip API response and immediately re-fetches state from the backend while it is still resolving the next audio stream.

2. **Guild not found** — the guild picker shows every guild the bot is in, not just guilds the user is also a member of. Selecting a guild the user isn't in leads to errors. The only working workaround is manually typing `?guild=<id>` in the URL. The fix is to store the user's guild list in the JWT at login time and filter the picker to only the intersection. Guild choice is remembered for the session (sessionStorage).

---

## Goals

- Skip a song from either the PlayerBar or QueueView without any flicker or clearing of the dashboard.
- Guild picker shows only guilds the user AND the bot share.
- After picking a guild, the choice is remembered for the session (no re-picking on page refresh within the same tab).
- No UI redesign — minimal, targeted patches only.

---

## User Stories

### US-001: Investigate and identify root cause of skip clearing

**Description:** As a developer, I need to confirm exactly why the dashboard clears after a skip before writing any fix.

**Acceptance Criteria:**
- [x] Read `PlayerBar.tsx:handleSkip` — confirm it discards the `skipTrack()` return value and calls `fetchData()` immediately after.
- [x] Read `bot/api/player.py:handle_queue_skip` — confirm `await _play_next()` runs before the response is sent, and that during URL resolution `fetchPlayback` can transiently return `state: stopped`.
- [x] Document the exact race in a code comment or in this story's findings before proceeding to US-002.

---

### US-002: Fix PlayerBar skip — use response data, avoid immediate re-fetch

**Description:** As a user, I want skipping from the player bar to instantly show the next song with no blank flash.

**Background:**
- `PlayerBar.handleSkip()` currently calls `await skipTrack(guildId)` but **throws away the return value**, then calls `fetchData()` immediately.
- `fetchData()` fires `fetchPlayback` + `fetchQueue` at a moment when the backend may still be resolving the next track's audio URL — `fetchPlayback` can return `state: stopped` and `fetchQueue` can return `current: null` during this window.
- `QueueView.handleSkip()` already does the right thing: it uses the `skipTrack()` return value to update state directly.

**Fix:**
- In `PlayerBar.handleSkip()`, after `await skipTrack(guildId)`:
  - Use the returned `QueueData` to update `currentTrack` immediately (same pattern as QueueView).
  - Do NOT call `fetchData()` immediately after the skip. Let the existing 5-second poll correct any drift.
  - Still call `onQueueChanged?.()` so QueueView also updates from the skip response.
- `skipTrack()` in `api.ts` already returns `{ current, tracks }` — no backend change needed.

**Acceptance Criteria:**
- [x] `PlayerBar.handleSkip` reads the return value of `skipTrack(guildId)` and calls `setCurrentTrack(updated.current)`.
- [x] `PlayerBar.handleSkip` does NOT call `fetchData()` immediately after the skip.
- [x] `onQueueChanged?.()` is still called so `QueueView` refreshes.
- [x] Skipping from the PlayerBar does not clear the "now playing" display or show "Nothing playing" transiently.
- [x] Skipping from QueueView (unchanged) still works correctly.
- [x] TypeScript typechecks pass (`npm run typecheck` or `tsc --noEmit`).

---

### US-003: Fix QueueView skip — prevent double-skip if PlayerBar and QueueView both trigger

**Description:** As a developer, I want to confirm there is no double API call when skip is triggered.

**Background:**
- `QueueView` has its own skip button on the current track row.
- `PlayerBar` also has a skip button that calls `onQueueChanged?.()` → triggers a `loadQueue()` in QueueView via `refreshTrigger`.
- These are separate skip buttons, not the same one — no double POST.
- However, after fixing US-002, the `onQueueChanged?.()` call from PlayerBar will trigger `QueueView` to `loadQueue()`. This refetch could again race with the backend.

**Fix:**
- In `QueueView`, the `refreshTrigger` effect calls `loadQueue()` which fires a fresh `fetchQueue`. This is fine — by the time `onQueueChanged` fires, the backend has already completed `_play_next` and the response includes the new current track.
- No change needed in QueueView for this story, but verify the behaviour holds after US-002 changes.

**Acceptance Criteria:**
- [x] After PlayerBar skip, QueueView shows the next track within the same render cycle (no "Queue is empty" flash).
- [x] No duplicate POST to `/api/queue/skip`.
- [x] TypeScript typechecks pass.

---

### US-004: Store user guild IDs in JWT at OAuth callback time

**Description:** As a developer, I need to persist the user's guild list in the JWT so the backend can filter guilds per user.

**Background:**
- `bot/api/auth.py:handle_auth_callback` already fetches `guilds_data` (the list of guilds the user is in) from Discord during OAuth.
- The JWT payload currently stores `{id, username, avatar, guild_id}` but does NOT store the user's guild list.
- `/api/guilds` returns all bot guilds with no user-aware filtering.

**Fix:**
- In `handle_auth_callback`, add `"guild_ids": [g["id"] for g in guilds_data]` to `session_payload` before encoding the JWT.
- This stores the full list of user guild IDs in the JWT cookie (they are Discord snowflake strings, a typical user is in 10–100 guilds — well within JWT limits).

**Acceptance Criteria:**
- [x] `session_payload` in `handle_auth_callback` includes a `guild_ids` key containing a list of guild ID strings.
- [x] The JWT is re-issued with this new field on every fresh login (existing sessions without `guild_ids` will just show all guilds until they re-login — acceptable).
- [x] Python typechecks / linting passes (`ruff check`).

---

### US-005: Filter /api/guilds to intersection of bot guilds and user guilds

**Description:** As a user, I want the guild picker to only show servers I am actually a member of (and that the bot is also in).

**Background:**
- `bot/api/guilds.py:handle_guilds_get` currently returns all guilds the bot is in, ignoring who the requesting user is.
- The JWT middleware already decodes the JWT and makes it available on `request["user"]` (or similar — check actual middleware).
- After US-004, the decoded JWT payload has `guild_ids`.

**Fix:**
- In `handle_guilds_get`, read the user's `guild_ids` from the decoded JWT (the middleware places decoded claims on `request`).
- Filter `bot.guilds` to only those whose `str(guild.id)` is in the user's `guild_ids`.
- If `guild_ids` is missing from the JWT (old session), fall back to returning all bot guilds (safe degradation).

**Acceptance Criteria:**
- [x] `GET /api/guilds` returns only guilds present in both `bot.guilds` and the JWT `guild_ids`.
- [x] If `guild_ids` is absent in the JWT, all bot guilds are returned (backward-compat fallback).
- [x] A user who is NOT in guild X cannot see guild X in the picker.
- [x] Python linting passes (`ruff check`).

---

### US-006: Remember selected guild in sessionStorage

**Description:** As a user, I want my selected guild to be remembered for the browser session so I don't have to re-pick it every time I refresh.

**Background:**
- Currently, guild is read exclusively from `?guild=<id>` in the URL (`App.tsx:getQueryParam`).
- If the user refreshes or navigates without the query param, they are sent back to the guild picker.
- The session should persist within the same tab (sessionStorage), but not across tabs or after closing (not localStorage per decision 4D).

**Fix (all changes in `dashboard/src/App.tsx`):**
- Define two helpers: `getSessionGuild(): string | undefined` and `setSessionGuild(id: string): void` that read/write `sessionStorage.getItem('selected_guild')`.
- After reading `guildId` from URL, if it is present: call `setSessionGuild(guildId)` to persist it.
- If `guildId` is not in the URL, fall back to `getSessionGuild()`.
- In `GuildPickerPage.handleGuildClick`, the navigation is `window.location.href = '/?guild=...'` which already puts the guild in URL — sessionStorage is updated on the next load. No change needed in GuildPickerPage.

**Acceptance Criteria:**
- [x] After navigating to `/?guild=123`, refreshing the page still shows the dashboard for guild 123 (no redirect to picker).
- [x] Opening a new tab does NOT inherit the guild (sessionStorage is tab-scoped).
- [x] Logging out clears the session guild (`sessionStorage.removeItem('selected_guild')` in the logout handler).
- [x] TypeScript typechecks pass.

---

### US-007: Auto-select guild if user is in exactly one common guild

**Description:** As a user who only has one server in common with the bot, I want to skip the guild picker entirely.

**Background:**
- After US-005, the guild picker only shows guilds the user and bot share.
- If that list has exactly one entry, the picker is redundant.

**Fix (in `GuildPickerPage.tsx`):**
- After `fetchGuilds()` resolves and the list has exactly 1 guild, automatically call `handleGuildClick(guilds[0].id)` instead of rendering the picker.
- If 0 guilds: show a "No common servers found" message instead of an empty grid.

**Acceptance Criteria:**
- [ ] User with exactly 1 common guild is redirected automatically — guild picker never renders.
- [ ] User with 0 common guilds sees an informative empty state message.
- [ ] User with 2+ common guilds sees the normal guild picker grid.
- [ ] TypeScript typechecks pass.
- [ ] Verify in browser using dev-browser skill.

---

## Functional Requirements

- FR-1: `PlayerBar.handleSkip` must apply the `skipTrack()` response to local state without calling `fetchData()` immediately.
- FR-2: After a skip from either PlayerBar or QueueView, no component may transiently render an empty/cleared state.
- FR-3: The JWT issued at OAuth callback must include `guild_ids: string[]` — all guild IDs the user is a member of.
- FR-4: `GET /api/guilds` must return only the intersection of bot guilds and the authenticated user's guilds (from JWT).
- FR-5: Selected guild must be stored in `sessionStorage` under key `selected_guild` and used as a fallback when `?guild` URL param is absent.
- FR-6: Guild picker must auto-select and redirect when only one guild is available.
- FR-7: Logging out must clear `selected_guild` from sessionStorage.

---

## Non-Goals

- No WebSocket or SSE real-time updates — polling stays at 5s.
- No localStorage persistence (resets on tab close is intentional).
- No UI redesign of the guild picker or player bar.
- No guild membership re-validation on every API call (only at login time).
- No support for adding the bot to a new guild from the dashboard.

---

## Technical Considerations

- **JWT size**: Adding `guild_ids` is safe. A user in 100 guilds adds ~1800 bytes of base64 to the cookie — well within the 4KB cookie limit.
- **Stale guild_ids**: If a user leaves or joins a guild after login, their JWT is stale until re-login. Acceptable for this scope.
- **Backward compatibility**: Old JWTs without `guild_ids` must not crash `/api/guilds` — use `.get("guild_ids")` with a `None` fallback.
- **Key files to change**:
  - `bot/api/auth.py` — add `guild_ids` to JWT payload
  - `bot/api/guilds.py` — filter guilds by user's `guild_ids`
  - `dashboard/src/App.tsx` — sessionStorage read/write, fallback logic
  - `dashboard/src/components/PlayerBar.tsx` — use skip response data
  - `dashboard/src/pages/GuildPickerPage.tsx` — auto-select single guild, empty state

---

## Success Metrics

- Skipping a song never renders "Nothing playing" or an empty queue transiently.
- A user who is not in a guild cannot reach that guild's dashboard via the picker.
- Refreshing the dashboard page does not redirect to the guild picker.

---

## Open Questions

- Should logging out also clear the `?guild` from the URL (i.e., navigate to `/`) or just clear sessionStorage? Assume navigate to `/` to avoid confusion.
- If the JWT middleware exposes decoded claims differently (e.g. `request["user"]` vs `request.get("jwt_payload")`), the exact key name in `handle_guilds_get` must be confirmed by reading `bot/api/auth.py`'s middleware before implementing US-005.
