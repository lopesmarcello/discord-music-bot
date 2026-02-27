"""Audio source resolver for YouTube and SoundCloud."""
from __future__ import annotations

import re
from dataclasses import dataclass


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


# URL detection patterns
_YOUTUBE_RE = re.compile(r"^https?://(www\.)?(youtube\.com|youtu\.be)/")
_SOUNDCLOUD_RE = re.compile(r"^https?://(www\.)?soundcloud\.com/")
_URL_RE = re.compile(r"^https?://")


class AudioResolver:
    """Resolves user queries and URLs into playable AudioTrack instances."""

    def __init__(self, ytdl_class=None) -> None:
        self._ytdl_class = ytdl_class

    # ------------------------------------------------------------------
    # Dependency accessors (lazy-import for production; injectable for tests)
    # ------------------------------------------------------------------

    def _get_ytdl_class(self):
        if self._ytdl_class is not None:
            return self._ytdl_class
        import yt_dlp  # pragma: no cover
        return yt_dlp.YoutubeDL  # pragma: no cover

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
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
