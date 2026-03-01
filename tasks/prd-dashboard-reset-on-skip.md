# PRD: Fix Dashboard Reset to Empty State on Skip

## Introduction

When a user adds a song via Discord slash commands (which connects the bot to a voice channel and registers the `on_track_end` callback), then adds another song via the dashboard, then skips the currently playing song from the dashboard — the bot continues playing correctly but the dashboard resets to an empty state (no current track, empty queue).

**Root cause:** The skip action calls `vm.stop()` followed by `await music._play_next(guild_id)`. Calling `vm.stop()` triggers the `on_track_end` callback that was set when the Discord `/play` command originally joined the voice channel. That callback schedules a second `_play_next(guild_id)` via `asyncio.run_coroutine_threadsafe`. The sequence becomes:

1. `vm.stop()` → fires `on_track_end` → schedules `_play_next` on the event loop
2. `await music._play_next(guild_id)` runs first (same coroutine) → pops track from queue, sets `_current_tracks[guild_id]`, starts playback ✅
3. The scheduled `_play_next` from step 1 now runs → queue is empty → sets `_current_tracks[guild_id] = None` ❌

The audio keeps playing because `vm.play()` was already called in step 2, but the in-memory metadata (`_current_tracks`) is wiped to `None` and the queue is empty. The dashboard then polls `GET /api/queue` and receives `{"current": null, "tracks": []}`, showing the empty state.

The same double-`_play_next` race exists in the Discord `/skip` command (`music.py:133-136`), which also calls `vm.stop()` then `_play_next` directly.

## Goals

- Eliminate the double `_play_next` invocation during skip so `_current_tracks` stays consistent with what is actually playing.
- Dashboard shows the correct now-playing track and queue after any skip (from Discord or the dashboard).
- No regression in the natural end-of-track behavior (song finishes on its own → next song plays correctly).

## User Stories

### US-001: Fix double `_play_next` race condition in skip

**Description:** As a developer, I need skip operations to call `_play_next` exactly once so the bot's in-memory state matches what is actually playing.

**Acceptance Criteria:**
- [ ] Introduce a `_skipping` flag (or equivalent) on `Music` per guild that is set to `True` before `vm.stop()` is called during a skip and cleared after `_play_next` completes.
- [ ] The `on_track_end` callback (`_make_on_track_end`) checks this flag: if `_skipping[guild_id]` is `True`, it does NOT schedule `_play_next` and instead clears the flag, leaving control to the explicit `_play_next` call.
- [ ] `music.py` Discord `/skip` command uses the same flag guard.
- [ ] `player.py` `handle_queue_skip` uses the same flag guard.
- [ ] After skip, `music._current_tracks[guild_id]` equals the track that is now actually playing (or `None` if queue was empty).
- [ ] After skip, `music._queue_registry.get_queue(guild_id).list()` reflects the remaining tracks correctly.
- [ ] Typecheck/lint passes.

### US-002: Verify dashboard stays in sync after skip

**Description:** As a user, I want the dashboard to show the correct now-playing song and queue immediately after I skip, whether the skip was triggered from Discord or the dashboard.

**Acceptance Criteria:**
- [ ] After skipping via the dashboard skip button: the dashboard's "Now Playing" section updates to the next song (or shows empty if no songs remain) — not a stale or empty state.
- [ ] After skipping via the Discord `/skip` command: the dashboard's next 5-second poll reflects the correct now-playing track.
- [ ] If the queue has only one song when skip is triggered, the dashboard correctly shows "empty queue" AND the bot stops playback (no phantom current track displayed).
- [ ] Typecheck/lint passes.

## Functional Requirements

- **FR-1:** Add a `_skipping: dict[int, bool]` attribute to the `Music` cog (keyed by `guild_id`, default `False`).
- **FR-2:** Before calling `vm.stop()` in any skip path (both `music.py:Music.skip` and `player.py:handle_queue_skip`), set `self._skipping[guild_id] = True`.
- **FR-3:** In `_make_on_track_end`'s inner `callback`, check `self._skipping.get(guild_id, False)`. If `True`, set `self._skipping[guild_id] = False` and return without scheduling `_play_next`.
- **FR-4:** After `await self._play_next(guild_id)` completes in a skip path, ensure `_skipping[guild_id]` is reset to `False` (it may already be `False` if the callback never fired, e.g. when the VoiceManager doesn't call `after` on explicit stop — the reset is a no-op in that case).
- **FR-5:** The natural end-of-track flow (song finishes on its own) must be unaffected: `_skipping` is `False` in that case, so the callback proceeds normally and schedules `_play_next`.

## Non-Goals

- No changes to the dashboard polling interval or frontend state management — the fix is purely on the bot/API side.
- No changes to the pause, resume, or stop (full disconnect) flows.
- No persistent queue storage — queue remains in-memory only.

## Technical Considerations

- **Files to change:** `bot/cogs/music.py` and `bot/api/player.py`.
- **Flag scope:** `_skipping` is per-guild (`dict[int, bool]`) to avoid cross-guild interference.
- **Thread safety:** The `on_track_end` callback runs in a different thread (discord.py audio thread). Reading and writing `_skipping[guild_id]` (a plain dict with a bool) is effectively safe here because the GIL protects individual dict reads/writes in CPython, and the flag is only read once per callback invocation.
- **Alternative approach considered:** Temporarily clearing `vm.on_track_end` before `stop()` and restoring it after, but this introduces more state and requires the VoiceManager to expose a mutable callback reference.

## Success Metrics

- After skip, `GET /api/queue` always returns a `current` value that matches the song the bot is actually playing.
- Zero instances of `_current_tracks[guild_id]` being set to `None` while audio is still playing.

## Open Questions

- Should the `_play_next` in `handle_queue_skip` (`player.py`) be changed to also call `vm.set_on_track_end` to ensure the callback is registered even when the API triggers the first play? (Currently `set_on_track_end` is only called via the Discord `/play` command when joining the channel.)
