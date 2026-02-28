"""YouTube search API route handler."""
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


async def handle_search(
    request: "aiohttp.web.Request",
    *,
    _resolver_factory=None,
) -> "aiohttp.web.Response":
    """GET /api/search?q={query}&limit={n} — search YouTube and return results."""
    import aiohttp.web  # noqa: PLC0415

    q = request.rel_url.query.get("q", "").strip()
    if not q:
        raise aiohttp.web.HTTPBadRequest(reason="q query parameter is required")

    try:
        limit = int(request.rel_url.query.get("limit", "5"))
    except ValueError:
        raise aiohttp.web.HTTPBadRequest(reason="limit must be an integer")

    limit = max(1, min(limit, 25))

    if _resolver_factory is not None:
        resolver = _resolver_factory()
    else:
        music = _get_music_cog(request)
        if music is not None:
            resolver = music._resolver
        else:
            from bot.audio.resolver import AudioResolver  # noqa: PLC0415
            resolver = AudioResolver()

    results = resolver.search(q, max_results=limit)

    return aiohttp.web.Response(
        text=json.dumps({"results": results}),
        content_type="application/json",
    )


def setup_search_routes(app: "aiohttp.web.Application") -> None:
    """Register search routes on the aiohttp application."""
    import aiohttp.web  # noqa: PLC0415

    app.router.add_get("/api/search", handle_search)
