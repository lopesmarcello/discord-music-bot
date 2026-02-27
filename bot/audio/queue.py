"""Per-guild in-memory song queue."""
from __future__ import annotations

from typing import Optional


class Queue:
    """An in-memory queue for a single guild."""

    def __init__(self) -> None:
        self._tracks: list = []

    def add(self, track: object) -> None:
        """Append a track to the end of the queue."""
        raise NotImplementedError("Queue.add() not yet implemented (US-003)")

    def next(self) -> Optional[object]:
        """Remove and return the front track, or None if empty."""
        raise NotImplementedError("Queue.next() not yet implemented (US-003)")

    def peek(self) -> Optional[object]:
        """Return the front track without removing it, or None if empty."""
        raise NotImplementedError("Queue.peek() not yet implemented (US-003)")

    def clear(self) -> None:
        """Remove all tracks from the queue."""
        raise NotImplementedError("Queue.clear() not yet implemented (US-003)")

    def list(self) -> list:
        """Return a copy of all tracks in order."""
        raise NotImplementedError("Queue.list() not yet implemented (US-003)")
