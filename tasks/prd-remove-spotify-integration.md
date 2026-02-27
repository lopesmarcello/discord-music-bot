# PRD: Remove Spotify Integration

## Introduction

The Discord music bot currently supports Spotify track URLs by calling the Spotify Web API to fetch track metadata (artist name, song title), then searching YouTube for the actual audio. This requires users to register a Spotify developer app and provide `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` environment variables just to run the bot.

Since Spotify only ever provided metadata — the actual audio stream already came from YouTube — this dependency is unnecessary overhead. This feature removes all Spotify integration: the `spotipy` library, the API credentials, and the Spotify URL resolution path. When a user pastes a Spotify URL, the bot will reject it with a helpful message directing them to search by song name instead.

## Goals

- Eliminate the `spotipy` dependency and the `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` env vars
- Remove all Spotify-specific code from the resolver, including detection, API calls, and the `_SPOTIFY_RE` regex
- When a Spotify URL is pasted, reply with a clear hint to search by song name instead
- Remove all Spotify references from documentation, config templates, and tests
- Reduce bot setup complexity (one fewer third-party developer account required)

## User Stories

### US-001: Remove spotipy dependency and env vars

**Description:** As a developer, I want to remove the `spotipy` package and Spotify credentials from the project so that the bot has no dependency on the Spotify API.

**Acceptance Criteria:**
- [ ] `spotipy` removed from `dependencies` in `pyproject.toml`
- [ ] `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` removed from `.env.example`
- [ ] Running `pip install -e .` does not install `spotipy`
- [ ] Typecheck passes

### US-002: Remove Spotify resolution code from resolver

**Description:** As a developer, I want to remove all Spotify-specific logic from `bot/audio/resolver.py` so that the codebase no longer references the Spotify API.

**Acceptance Criteria:**
- [ ] `_SPOTIFY_RE` regex pattern removed from `resolver.py`
- [ ] `_resolve_spotify()` method removed from `AudioResolver`
- [ ] `_get_spotipy_client()` method removed from `AudioResolver`
- [ ] `_spotipy_client` instance variable removed from `AudioResolver.__init__`
- [ ] All `import spotipy` / `from spotipy` statements removed
- [ ] The `resolve()` dispatch method no longer has a Spotify branch
- [ ] Typecheck passes

### US-003: Return helpful error when Spotify URL is pasted

**Description:** As a user, I want to receive a clear message when I paste a Spotify URL so that I know the bot doesn't support it and what to do instead.

**Acceptance Criteria:**
- [ ] When `resolve()` receives a Spotify URL (`https://open.spotify.com/...`), it raises `UnsupportedSourceError` (or equivalent)
- [ ] The music cog catches the error and replies with a message such as: "Spotify URLs are not supported. Try searching by song name, e.g. `/play artist - song title`"
- [ ] The error message is sent as a Discord reply (not silent)
- [ ] Other unsupported URLs are unaffected
- [ ] Typecheck passes

### US-004: Remove Spotify unit tests

**Description:** As a developer, I want to remove all Spotify-related test cases so that the test suite no longer references removed code.

**Acceptance Criteria:**
- [ ] `TestResolveSpotify` test class removed from `tests/unit/test_resolver.py`
- [ ] No remaining references to `spotipy`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, or `_resolve_spotify` in any test file
- [ ] All remaining tests continue to pass
- [ ] Typecheck passes

### US-005: Remove Spotify from documentation and config

**Description:** As a developer, I want all project documentation and config templates to reflect that Spotify is no longer supported so that new users aren't confused by references to removed features.

**Acceptance Criteria:**
- [ ] `README.md` no longer mentions Spotify, `SPOTIFY_CLIENT_ID`, or `SPOTIFY_CLIENT_SECRET`
- [ ] `.env.example` does not include Spotify credential entries
- [ ] README documents that Spotify URLs are not supported and users should search by song name
- [ ] Typecheck passes

## Functional Requirements

- FR-1: `pyproject.toml` must not list `spotipy` as a dependency
- FR-2: `.env.example` must not include `SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET`
- FR-3: `bot/audio/resolver.py` must contain no Spotify-specific regex, methods, imports, or instance variables
- FR-4: When `resolve()` receives a URL matching `open.spotify.com`, it must raise an error (not silently fall through to yt-dlp)
- FR-5: The music cog must catch the unsupported-source error for Spotify URLs and reply with a user-facing message that explains the limitation and suggests searching by song name
- FR-6: All unit tests for Spotify resolution must be deleted
- FR-7: `README.md` and `.env.example` must be updated to remove all Spotify references

## Non-Goals

- No support for extracting track name from a Spotify URL without the API (e.g. parsing slug from URL)
- No support for Spotify playlists or albums (these were never supported)
- No changes to YouTube, SoundCloud, or text-search resolution paths
- No changes to the queue, voice, or playback systems

## Technical Considerations

- The `resolve()` method in `resolver.py` currently dispatches on URL pattern. After removal, a Spotify URL match should either raise `UnsupportedSourceError` directly, or fall through to the generic-URL handler which already raises `UnsupportedSourceError` — confirm which approach keeps the code simplest
- The music cog (`bot/cogs/music.py`) already has error handling for `UnsupportedSourceError`; verify it produces a user-visible reply and update the message to be Spotify-specific if the URL is a Spotify URL, or use a generic message that covers all unsupported URLs
- `AudioTrack.source` field currently accepts `"spotify"` as a value — after removal, this value will never appear; no code change is needed for the dataclass itself, but verify no downstream code checks `source == "spotify"`

## Success Metrics

- Zero references to `spotipy`, `SPOTIFY_CLIENT_ID`, or `SPOTIFY_CLIENT_SECRET` in the codebase after this change
- All existing tests pass
- Bot starts successfully with only `DISCORD_TOKEN` set (no Spotify vars needed)
- A user pasting a Spotify URL receives an informative reply within one bot response

## Open Questions

- Should the Spotify-specific error message differ from the generic unsupported-URL message, or is a single message for all unsupported sources sufficient? (Current plan: single generic message is fine)
- Are there any integration tests that exercise the Spotify flow and need to be deleted alongside the unit tests?
