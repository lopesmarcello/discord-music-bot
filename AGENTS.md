# Discord Music Bot — AI Agent Guide

This file is the primary reference for AI coding agents (Claude Code, Codex, Gemini, Copilot, etc.) working on this codebase. Read this before making any changes.

## Project Overview

A self-hosted Discord music bot (Python 3.11+) with a React/TypeScript dashboard. The bot streams audio from YouTube and SoundCloud into Discord voice channels. A browser dashboard provides queue management and playback controls via REST API.

## Architecture

```
bot/                  Python backend (discord.py + aiohttp)
  api/                REST API handlers (auth, player, search, guilds, health)
  audio/              Audio processing (resolver, queue, voice)
  cogs/               Discord command handlers
  services/           Shared service layer (MusicService)
dashboard/            React + TypeScript + Vite frontend (served by nginx)
tests/                pytest test suite (unit + integration + API)
```

### Key Design Decisions

- **MusicService facade** (`bot/services/music.py`): Owns all playback state (current_tracks, started_at, elapsed_offset, skipping). Both the Music cog and API handlers access state through this service — never access cog private attributes directly.
- **Dependency injection**: All major classes accept injectable dependencies for testing (resolver, queue_registry, voice_managers, ffmpeg_source_class).
- **Lazy imports**: `aiohttp.web` is imported inside functions (not at module level) so test stubs in `conftest.py` work without installing aiohttp.
- **Per-guild isolation**: Each guild gets its own Queue, VoiceManager, and playback state via `GuildQueueRegistry`.
- **JWT auth**: Discord OAuth2 flow issues JWT cookies (24h expiration, httponly, SameSite=Lax). All `/api/*` routes require valid JWT. `/auth/*` and `/health` are public.
- **Per-guild authorization**: Player endpoints verify the requesting user's JWT `guild_ids` contains the target `guild_id`.
- **Health checks**: Bot exposes `GET /health` (`{status, bot_ready}`). Dashboard nginx exposes `GET /health` (self-check) and `GET /health/bot` (proxied bot health). Both containers have Docker healthchecks in `docker-compose.yml`. Dashboard uses `depends_on: condition: service_healthy` to wait for the bot before starting.

## Commands

```bash
# Run tests (must pass before committing)
pytest --cov --cov-report=term-missing --cov-fail-under=70

# Lint (must pass before committing)
ruff check bot/ tests/

# Format check (must pass before committing)
ruff format --check bot/ tests/

# Auto-fix lint issues
ruff check --fix bot/ tests/

# Auto-format
ruff format bot/ tests/

# Dashboard typecheck
cd dashboard && npm run typecheck

# Run the bot locally
python -m bot
```

## Code Style Rules

- **Python**: Ruff with rules E, F, W. Line length 88. Format enforced.
- **Lint scope**: Both `bot/` and `tests/` must pass ruff check and format.
- **TypeScript**: Strict mode, checked via `tsc -b --noEmit`.
- **Logging**: Use `_log = logging.getLogger(__name__)` pattern. Use `%s`/`%r` formatting in log calls (not f-strings).
- **Imports in API handlers**: Use lazy imports inside functions (`import aiohttp.web  # noqa: PLC0415`).
- **No hardcoded secrets**: All secrets come from environment variables.

## Testing Patterns

- **Test stubs**: `tests/conftest.py` stubs `aiohttp` and `jwt` modules via `sys.modules` before any test imports. The fake JWT module does NOT verify signatures — it base64-decodes payloads.
- **Integration test stubs**: `tests/integration/conftest.py` stubs `discord`, `discord.ext`, and `discord.ext.commands`.
- **Mock helpers**: Tests use `_make_music_cog()`, `_make_request()`, `_make_vm()`, `_make_track()` helpers. Player API tests mock the `MusicService` (via `cog.service`), not cog internals.
- **Async tests**: Use `asyncio.run()` to run async handlers in sync test functions.
- **Coverage threshold**: CI enforces minimum 70% coverage.

## CI/CD Pipeline

| Job | What it checks |
|-----|---------------|
| `test-bot` | pytest with coverage + ruff check + ruff format on `bot/` and `tests/` |
| `lint-dashboard` | TypeScript typecheck |
| `build-docker` | Docker build validation for bot and dashboard images |

CI runs on push to `main` and on all PRs to `main`. Deploy is a separate workflow with environment selector (development/production) that gates on CI status.

## File Naming Conventions

- **Tests mirror source**: `bot/api/player.py` -> `tests/test_player_api.py`
- **Integration tests**: `tests/integration/test_{command}_command.py`
- **Unit tests**: `tests/unit/test_{module}.py`

## Common Pitfalls

- **Never access `cog._*` from API handlers**. Use `cog.service.*` instead. The MusicService owns all playback state.
- **guild_ids in JWT are strings** (from Discord API), but `guild_id` from query params is parsed as `int`. Compare with `str(guild_id)`.
- **Don't forget `# noqa: PLC0415`** on lazy imports inside functions.
- **Test requests need `jwt_payload`**: When testing player endpoints with a bot present, pass `jwt_payload={"guild_ids": ["123"]}` to `_make_request()` for guild authorization to pass.
- **conftest stubs must load first**: Never import `bot.api.*` at module level in test files without ensuring conftest stubs are registered.

## Adding a New API Endpoint

1. Create handler in the appropriate `bot/api/*.py` file
2. Use lazy imports: `import aiohttp.web  # noqa: PLC0415, F401`
3. Get service via `_get_service(request)` (for player-related) or `_get_music_cog(request)` (for cog access)
4. Add `_require_guild_id(request)` and `_require_guild_membership(request, guild_id)` if guild-scoped
5. Register route in the file's `setup_*_routes()` function
6. If the endpoint should be public (no JWT), add path exemption in `make_jwt_middleware()` in `auth.py`
7. Add tests following existing patterns in `tests/test_*_api.py`
8. Run `ruff check bot/ tests/` and `ruff format bot/ tests/` before committing

## Adding a New Bot Command

1. Add the command method to `bot/cogs/music.py` using `@commands.hybrid_command()`
2. Access state through `self.service.*` (not private attributes)
3. Add integration tests in `tests/integration/test_{command}_command.py`
4. Follow existing patterns: check voice state, use VoiceManager, send user feedback

## Branch and PR Rules

- Branch from `main`, target PRs to `main`
- Branch prefixes: `feat/`, `fix/`, `chore/`, `docs/`
- All CI checks must pass before merge
- Commit messages: imperative present tense, under 72 chars
