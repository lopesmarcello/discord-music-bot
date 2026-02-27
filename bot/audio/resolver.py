"""Audio source resolver for YouTube, Spotify, and SoundCloud."""
from __future__ import annotations

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
    source: str  # "youtube", "spotify", "soundcloud", "search"


class AudioResolver:
    """Resolves user queries and URLs into playable AudioTrack instances."""

    def resolve(self, query: str) -> AudioTrack:
        """Resolve a query or URL to an AudioTrack.

        Args:
            query: A URL (YouTube, Spotify, SoundCloud) or plain search string.

        Returns:
            An AudioTrack with stream information.

        Raises:
            UnsupportedSourceError: If the URL is unrecognised.
        """
        raise NotImplementedError("AudioResolver.resolve() not yet implemented (US-002)")
