"""Audio source resolver for YouTube and SoundCloud."""
from __future__ import annotations

import json as _json
import logging
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

_log = logging.getLogger(__name__)


class UnsupportedSourceError(Exception):
    """Raised when the source URL or query is not supported."""


@dataclass
class AudioTrack:
    """Represents a resolved audio track."""

    title: str
    url: str
    stream_url: str
    duration: int  # seconds
    source: str  # "youtube", "soundcloud", "search"
    thumbnail: str = ""  # empty string when unavailable


# URL detection patterns
_YOUTUBE_RE = re.compile(r"^https?://(www\.)?(youtube\.com|youtu\.be)/")
_SOUNDCLOUD_RE = re.compile(r"^https?://(www\.)?soundcloud\.com/")
_URL_RE = re.compile(r"^https?://")

_ISO8601_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_iso8601_duration(duration: str) -> int:
    """Convert an ISO 8601 duration string (e.g. PT3M45S) to seconds."""
    match = _ISO8601_DURATION_RE.match(duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


_YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class AudioResolver:
    """Resolves user queries and URLs into playable AudioTrack instances."""

    def __init__(self, ytdl_class=None, _http_get_fn=None) -> None:
        self._ytdl_class = ytdl_class
        # Injectable for testing; defaults to urllib.request.urlopen
        self._http_get_fn = _http_get_fn if _http_get_fn is not None else urllib.request.urlopen

    # ------------------------------------------------------------------
    # Dependency accessors (lazy-import for production; injectable for tests)
    # ------------------------------------------------------------------

    def _get_ytdl_class(self):
        if self._ytdl_class is not None:
            return self._ytdl_class
        import yt_dlp  # pragma: no cover
        return yt_dlp.YoutubeDL  # pragma: no cover

    def _fetch_json(self, url: str) -> dict:
        """GET *url* and return the parsed JSON body."""
        with self._http_get_fn(url) as resp:
            return _json.loads(resp.read())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_info(self, url_or_query: str) -> dict:
        """Run yt_dlp extraction and return the info dict for a single entry."""
        YoutubeDL = self._get_ytdl_class()
        ydl_opts = {"format": "bestaudio/best", "noplaylist": True, "quiet": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_or_query, download=False)
        # Search queries return a wrapper dict with an 'entries' list
        if info and "entries" in info:
            info = info["entries"][0]
        return info

    def _make_track(self, info: dict, original_url: str, source: str) -> AudioTrack:
        return AudioTrack(
            title=info["title"],
            url=info.get("webpage_url", original_url),
            stream_url=info["url"],
            duration=info.get("duration", 0),
            source=source,
            thumbnail=info.get("thumbnail", ""),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------

    def _search_youtube_api(self, query: str, max_results: int, api_key: str) -> list:
        """Search via YouTube Data API v3; returns list of result dicts."""
        search_params = urllib.parse.urlencode({
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": max_results,
            "key": api_key,
        })
        search_data = self._fetch_json(f"{_YOUTUBE_API_BASE}/search?{search_params}")
        items = search_data.get("items", [])
        if not items:
            return []

        video_ids = [item["id"]["videoId"] for item in items]

        videos_params = urllib.parse.urlencode({
            "part": "contentDetails",
            "id": ",".join(video_ids),
            "key": api_key,
        })
        videos_data = self._fetch_json(f"{_YOUTUBE_API_BASE}/videos?{videos_params}")
        duration_map: dict[str, int] = {}
        for vid in videos_data.get("items", []):
            duration_map[vid["id"]] = _parse_iso8601_duration(
                vid["contentDetails"]["duration"]
            )

        results = []
        for item, vid_id in zip(items, video_ids):
            snippet = item["snippet"]
            thumbnails = snippet.get("thumbnails", {})
            thumbnail = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or ""
            )
            results.append({
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "duration": duration_map.get(vid_id, 0),
                "thumbnail": thumbnail,
            })
        return results

    def _search_ytdlp_scsearch(self, query: str, max_results: int) -> list:
        """Search SoundCloud via yt-dlp scsearch prefix."""
        YoutubeDL = self._get_ytdl_class()
        ydl_opts = {"format": "bestaudio/best", "noplaylist": True, "quiet": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"scsearch{max_results}:{query}", download=False)
        entries = (info or {}).get("entries", [])
        results = []
        for entry in entries:
            if entry:
                results.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("webpage_url", ""),
                    "duration": entry.get("duration", 0),
                    "thumbnail": entry.get("thumbnail", ""),
                })
        return results

    def search(self, query: str, max_results: int = 5) -> list:
        """Search for videos matching *query*.

        Uses YouTube Data API v3 when YOUTUBE_API_KEY is set in the
        environment; falls back to SoundCloud via yt-dlp otherwise.  If the
        YouTube API call raises any exception, a warning is logged and the
        SoundCloud fallback is used instead.

        Returns a list of result dicts with title, url, duration, thumbnail.
        """
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            try:
                return self._search_youtube_api(query, max_results, api_key)
            except Exception as exc:
                _log.warning("YouTube API search failed, falling back to SoundCloud: %s", exc)
        return self._search_ytdlp_scsearch(query, max_results)

    def resolve(self, query: str) -> AudioTrack:
        """Resolve a query or URL to an AudioTrack.

        Args:
            query: A URL (YouTube, SoundCloud) or plain search string.

        Returns:
            An AudioTrack with stream information.

        Raises:
            UnsupportedSourceError: If the URL scheme is recognised but the
                platform is not supported.
        """
        if _YOUTUBE_RE.match(query):
            info = self._extract_info(query)
            return self._make_track(info, query, "youtube")

        if _SOUNDCLOUD_RE.match(query):
            info = self._extract_info(query)
            return self._make_track(info, query, "soundcloud")

        if _URL_RE.match(query):
            raise UnsupportedSourceError(f"Unsupported URL: {query}")

        # Plain search string → search YouTube
        info = self._extract_info(f"ytsearch1:{query}")
        return self._make_track(info, query, "search")
