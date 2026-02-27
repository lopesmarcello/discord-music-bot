"""Unit tests for Queue and GuildQueueRegistry (US-003)."""
from __future__ import annotations

import pytest

from bot.audio.resolver import AudioTrack
from bot.audio.queue import Queue, GuildQueueRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_track(title: str = "Song", n: int = 1) -> AudioTrack:
    return AudioTrack(
        title=title,
        url=f"https://youtube.com/watch?v={n}",
        stream_url=f"https://stream.example.com/{n}.webm",
        duration=180,
        source="youtube",
    )


# ---------------------------------------------------------------------------
# Queue – add()
# ---------------------------------------------------------------------------

class TestQueueAdd:
    def test_add_single_track(self):
        q = Queue()
        track = _make_track("First")
        q.add(track)
        assert q.peek() is track

    def test_add_multiple_tracks_preserves_order(self):
        q = Queue()
        t1, t2, t3 = _make_track("A", 1), _make_track("B", 2), _make_track("C", 3)
        q.add(t1)
        q.add(t2)
        q.add(t3)
        tracks = q.list()
        assert tracks[0] is t1
        assert tracks[1] is t2
        assert tracks[2] is t3

    def test_add_returns_none(self):
        q = Queue()
        result = q.add(_make_track())
        assert result is None


# ---------------------------------------------------------------------------
# Queue – next()
# ---------------------------------------------------------------------------

class TestQueueNext:
    def test_next_returns_front_track(self):
        q = Queue()
        t1, t2 = _make_track("A", 1), _make_track("B", 2)
        q.add(t1)
        q.add(t2)
        assert q.next() is t1

    def test_next_removes_front_track(self):
        q = Queue()
        t1, t2 = _make_track("A", 1), _make_track("B", 2)
        q.add(t1)
        q.add(t2)
        q.next()
        assert q.peek() is t2

    def test_next_on_empty_queue_returns_none(self):
        q = Queue()
        assert q.next() is None

    def test_next_empties_single_item_queue(self):
        q = Queue()
        q.add(_make_track())
        q.next()
        assert q.next() is None

    def test_next_reduces_length(self):
        q = Queue()
        q.add(_make_track("A", 1))
        q.add(_make_track("B", 2))
        q.next()
        assert len(q.list()) == 1


# ---------------------------------------------------------------------------
# Queue – peek()
# ---------------------------------------------------------------------------

class TestQueuePeek:
    def test_peek_returns_front_track_without_removing(self):
        q = Queue()
        track = _make_track()
        q.add(track)
        peeked = q.peek()
        assert peeked is track
        # Track should still be in queue
        assert q.next() is track

    def test_peek_on_empty_queue_returns_none(self):
        q = Queue()
        assert q.peek() is None

    def test_repeated_peek_returns_same_track(self):
        q = Queue()
        track = _make_track()
        q.add(track)
        assert q.peek() is track
        assert q.peek() is track


# ---------------------------------------------------------------------------
# Queue – clear()
# ---------------------------------------------------------------------------

class TestQueueClear:
    def test_clear_empties_queue(self):
        q = Queue()
        q.add(_make_track("A", 1))
        q.add(_make_track("B", 2))
        q.clear()
        assert q.next() is None

    def test_clear_returns_none(self):
        q = Queue()
        q.add(_make_track())
        result = q.clear()
        assert result is None

    def test_clear_on_empty_queue_is_idempotent(self):
        q = Queue()
        q.clear()  # Should not raise
        assert q.next() is None

    def test_clear_then_add_works(self):
        q = Queue()
        q.add(_make_track("A", 1))
        q.clear()
        t2 = _make_track("B", 2)
        q.add(t2)
        assert q.peek() is t2


# ---------------------------------------------------------------------------
# Queue – list()
# ---------------------------------------------------------------------------

class TestQueueList:
    def test_list_returns_all_tracks_in_order(self):
        q = Queue()
        t1, t2 = _make_track("A", 1), _make_track("B", 2)
        q.add(t1)
        q.add(t2)
        result = q.list()
        assert result == [t1, t2]

    def test_list_returns_copy_not_reference(self):
        q = Queue()
        t = _make_track()
        q.add(t)
        lst = q.list()
        lst.clear()
        # Modifying the returned list must not affect the internal queue
        assert q.peek() is t

    def test_list_empty_queue_returns_empty_list(self):
        q = Queue()
        assert q.list() == []

    def test_list_does_not_consume_tracks(self):
        q = Queue()
        q.add(_make_track("A", 1))
        q.add(_make_track("B", 2))
        q.list()  # call list...
        assert len(q.list()) == 2  # ...queue unchanged


# ---------------------------------------------------------------------------
# GuildQueueRegistry – per-guild isolation
# ---------------------------------------------------------------------------

class TestGuildQueueRegistry:
    def test_get_queue_returns_queue_instance(self):
        registry = GuildQueueRegistry()
        q = registry.get_queue(guild_id=111)
        assert isinstance(q, Queue)

    def test_get_queue_same_guild_returns_same_instance(self):
        registry = GuildQueueRegistry()
        q1 = registry.get_queue(guild_id=111)
        q2 = registry.get_queue(guild_id=111)
        assert q1 is q2

    def test_different_guilds_have_isolated_queues(self):
        registry = GuildQueueRegistry()
        q1 = registry.get_queue(guild_id=111)
        q2 = registry.get_queue(guild_id=222)
        t = _make_track()
        q1.add(t)
        # Guild 222's queue must be empty
        assert q2.next() is None

    def test_delete_queue_removes_guild_entry(self):
        registry = GuildQueueRegistry()
        q1 = registry.get_queue(guild_id=111)
        q1.add(_make_track())
        registry.delete_queue(guild_id=111)
        # After deletion, a fresh queue should be returned
        q2 = registry.get_queue(guild_id=111)
        assert q2.next() is None

    def test_delete_nonexistent_queue_is_safe(self):
        registry = GuildQueueRegistry()
        registry.delete_queue(guild_id=999)  # Should not raise

    def test_multiple_guilds_are_independent(self):
        registry = GuildQueueRegistry()
        t1 = _make_track("Guild A Song", 1)
        t2 = _make_track("Guild B Song", 2)
        registry.get_queue(111).add(t1)
        registry.get_queue(222).add(t2)
        assert registry.get_queue(111).peek() is t1
        assert registry.get_queue(222).peek() is t2
