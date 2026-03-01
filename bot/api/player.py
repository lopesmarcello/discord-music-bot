"""Queue and playback API route handlers."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp.web


def _get_music_cog(request: "aiohttp.web.Request"):
    """Return the Music cog from the bot stored in the app, or None."""
    bot = request.app.get("bot")
    if bot is None:
        return None
    return bot.cogs.get("Music")


def _require_guild_id(request: "aiohttp.web.Request") -> int:
    """Parse guild_id from query params, or raise HTTPBadRequest."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id_str = request.rel_url.query.get("guild_id", "")
    if not guild_id_str:
        raise aiohttp.web.HTTPBadRequest(reason="guild_id query parameter is required")
    try:
        return int(guild_id_str)
    except ValueError:
        raise aiohttp.web.HTTPBadRequest(reason="guild_id must be an integer")


def _track_dict(track) -> dict:
    return {
        "title": track.title,
        "url": track.url,
        "duration": track.duration,
        "source": track.source,
        "thumbnail": track.thumbnail,
    }


async def handle_queue_get(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /api/queue?guild_id={id} — return current track and upcoming queue."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        return aiohttp.web.Response(
            text=json.dumps({"current": None, "tracks": []}),
            content_type="application/json",
        )

    current = music._current_tracks.get(guild_id)
    queue = music._queue_registry.get_queue(guild_id)
    tracks = queue.list()

    return aiohttp.web.Response(
        text=json.dumps({
            "current": _track_dict(current) if current is not None else None,
            "tracks": [_track_dict(t) for t in tracks],
        }),
        content_type="application/json",
    )


async def handle_queue_skip(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """POST /api/queue/skip?guild_id={id} — skip the current track."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        raise aiohttp.web.HTTPServiceUnavailable(reason="Music cog not available")

    vm = music._get_voice_manager(guild_id)
    if not vm.is_playing() and not vm.is_paused():
        raise aiohttp.web.HTTPBadRequest(reason="Nothing is currently playing")

    music._skipping[guild_id] = True
    vm.stop()
    await music._play_next(guild_id)
    music._skipping[guild_id] = False

    current = music._current_tracks.get(guild_id)
    queue = music._queue_registry.get_queue(guild_id)
    tracks = queue.list()
    return aiohttp.web.Response(
        text=json.dumps({
            "skipped": True,
            "current": _track_dict(current) if current is not None else None,
            "tracks": [_track_dict(t) for t in tracks],
        }),
        content_type="application/json",
    )


async def handle_queue_clear(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """POST /api/queue/clear?guild_id={id} — clear the upcoming queue."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        raise aiohttp.web.HTTPServiceUnavailable(reason="Music cog not available")

    queue = music._queue_registry.get_queue(guild_id)
    queue.clear()

    return aiohttp.web.Response(
        text=json.dumps({"cleared": True}),
        content_type="application/json",
    )


async def handle_queue_add(
    request: "aiohttp.web.Request",
    *,
    _resolver_factory=None,
) -> "aiohttp.web.Response":
    """POST /api/queue/add?guild_id={id} — add a track by URL to the queue."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        raise aiohttp.web.HTTPServiceUnavailable(reason="Music cog not available")

    body = await request.json()
    url = (body.get("url") or "").strip() if isinstance(body, dict) else ""
    if not url:
        raise aiohttp.web.HTTPBadRequest(reason="url field is required")

    if _resolver_factory is not None:
        resolver = _resolver_factory()
    else:
        resolver = music._resolver

    try:
        from bot.audio.resolver import UnsupportedSourceError  # noqa: PLC0415
        track = resolver.resolve(url)
    except UnsupportedSourceError as exc:
        raise aiohttp.web.HTTPBadRequest(reason=str(exc))

    vm = music._get_voice_manager(guild_id)
    if not vm.is_connected():
        raise aiohttp.web.HTTPConflict(
            reason="Bot is not in a voice channel. Use /join in Discord first."
        )

    queue = music._queue_registry.get_queue(guild_id)
    queue.add(track)

    if not vm.is_playing() and not vm.is_paused():
        await music._play_next(guild_id)

    return aiohttp.web.Response(
        text=json.dumps({
            "added": True,
            "track": _track_dict(track),
        }),
        content_type="application/json",
    )


async def handle_playback_get(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /api/playback?guild_id={id} — return current playback state."""
    import time  # noqa: PLC0415
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        return aiohttp.web.Response(
            text=json.dumps({"state": "stopped", "elapsed_seconds": None}),
            content_type="application/json",
        )

    vm = music._get_voice_manager(guild_id)
    if vm.is_playing():
        state = "playing"
    elif vm.is_paused():
        state = "paused"
    else:
        state = "stopped"

    if state == "stopped":
        elapsed_seconds = None
    elif state == "playing":
        started_at = music._started_at.get(guild_id)
        offset = music._elapsed_offset.get(guild_id, 0.0)
        elapsed_seconds = (
            (time.time() - started_at + offset)
            if started_at is not None
            else None
        )
    else:  # paused
        elapsed_seconds = music._elapsed_offset.get(guild_id, 0.0)

    return aiohttp.web.Response(
        text=json.dumps({"state": state, "elapsed_seconds": elapsed_seconds}),
        content_type="application/json",
    )


async def handle_playback_pause(
    request: "aiohttp.web.Request",
) -> "aiohttp.web.Response":
    """POST /api/playback/pause?guild_id={id} — pause playback."""
    import time  # noqa: PLC0415
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        raise aiohttp.web.HTTPServiceUnavailable(reason="Music cog not available")

    vm = music._get_voice_manager(guild_id)
    if not vm.is_playing():
        raise aiohttp.web.HTTPBadRequest(reason="Nothing is currently playing")

    started_at = music._started_at.get(guild_id)
    if started_at is not None:
        music._elapsed_offset[guild_id] = (
            music._elapsed_offset.get(guild_id, 0.0) + (time.time() - started_at)
        )
        music._started_at[guild_id] = None
    vm.pause()
    return aiohttp.web.Response(
        text=json.dumps({"paused": True}),
        content_type="application/json",
    )


async def handle_playback_resume(
    request: "aiohttp.web.Request",
) -> "aiohttp.web.Response":
    """POST /api/playback/resume?guild_id={id} — resume playback."""
    import time  # noqa: PLC0415
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        raise aiohttp.web.HTTPServiceUnavailable(reason="Music cog not available")

    vm = music._get_voice_manager(guild_id)
    if not vm.is_paused():
        raise aiohttp.web.HTTPBadRequest(reason="Playback is not paused")

    vm.resume()
    music._started_at[guild_id] = time.time()
    return aiohttp.web.Response(
        text=json.dumps({"resumed": True}),
        content_type="application/json",
    )


async def handle_playback_stop(
    request: "aiohttp.web.Request",
) -> "aiohttp.web.Response":
    """POST /api/playback/stop?guild_id={id} — stop playback and disconnect."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = _require_guild_id(request)
    music = _get_music_cog(request)

    if music is None:
        raise aiohttp.web.HTTPServiceUnavailable(reason="Music cog not available")

    vm = music._get_voice_manager(guild_id)
    if not vm.is_connected():
        raise aiohttp.web.HTTPBadRequest(reason="Not in a voice channel")

    vm.stop()
    music._started_at[guild_id] = None
    music._elapsed_offset[guild_id] = 0.0
    queue = music._queue_registry.get_queue(guild_id)
    queue.clear()
    music._current_tracks[guild_id] = None
    await vm.leave()

    return aiohttp.web.Response(
        text=json.dumps({"stopped": True}),
        content_type="application/json",
    )


def setup_player_routes(app: "aiohttp.web.Application") -> None:
    """Register queue and playback routes on the aiohttp application."""
    import aiohttp.web  # noqa: PLC0415, F401

    app.router.add_get("/api/queue", handle_queue_get)
    app.router.add_post("/api/queue/add", handle_queue_add)
    app.router.add_post("/api/queue/skip", handle_queue_skip)
    app.router.add_post("/api/queue/clear", handle_queue_clear)
    app.router.add_get("/api/playback", handle_playback_get)
    app.router.add_post("/api/playback/pause", handle_playback_pause)
    app.router.add_post("/api/playback/resume", handle_playback_resume)
    app.router.add_post("/api/playback/stop", handle_playback_stop)
