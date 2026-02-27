"""Smoke test verifying the project scaffold is correctly set up."""
from bot.audio.resolver import AudioTrack, AudioResolver, UnsupportedSourceError
from bot.audio.queue import Queue
from bot.audio.voice import VoiceManager


def test_audio_track_dataclass() -> None:
    """AudioTrack can be instantiated with the expected fields."""
    track = AudioTrack(
        title="Test Song",
        url="https://example.com",
        stream_url="https://stream.example.com",
        duration=180,
        source="youtube",
    )
    assert track.title == "Test Song"
    assert track.duration == 180
    assert track.source == "youtube"


def test_unsupported_source_error_is_exception() -> None:
    """UnsupportedSourceError is a subclass of Exception."""
    err = UnsupportedSourceError("bad url")
    assert isinstance(err, Exception)


def test_audio_resolver_exists() -> None:
    """AudioResolver class can be imported and instantiated."""
    resolver = AudioResolver()
    assert resolver is not None


def test_queue_exists() -> None:
    """Queue class can be imported and instantiated."""
    queue = Queue()
    assert queue is not None


def test_voice_manager_exists() -> None:
    """VoiceManager class can be imported and instantiated."""
    vm = VoiceManager()
    assert vm is not None
