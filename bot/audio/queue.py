"""Per-guild in-memory song queue."""
from __future__ import annotations

from typing import Optional


class Queue:
    """An in-memory queue for a single guild."""

    def __init__(self) -> None:
        self._tracks: list = []

    def add(self, track: object) -> None:
        """Append a track to the end of the queue."""
        self._tracks.append(track)

    def next(self) -> Optional[object]:
        """Remove and return the front track, or None if empty."""
        if not self._tracks:
            return None
        return self._tracks.pop(0)

    def peek(self) -> Optional[object]:
        """Return the front track without removing it, or None if empty."""
        if not self._tracks:
            return None
        return self._tracks[0]

    def clear(self) -> None:
        """Remove all tracks from the queue."""
        self._tracks.clear()

    def list(self) -> list:
        """Return a copy of all tracks in order."""
        return list(self._tracks)


class GuildQueueRegistry:
    """Manages isolated Queue instances keyed by guild ID."""

    def __init__(self) -> None:
        self._queues: dict[int, Queue] = {}

    def get_queue(self, guild_id: int) -> Queue:
        """Return the Queue for the given guild, creating it if needed."""
        if guild_id not in self._queues:
            self._queues[guild_id] = Queue()
        return self._queues[guild_id]

    def delete_queue(self, guild_id: int) -> None:
        """Remove the Queue for the given guild (no-op if not present)."""
        self._queues.pop(guild_id, None)
