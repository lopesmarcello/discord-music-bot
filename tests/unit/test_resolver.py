"""Unit tests for AudioResolver."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from bot.audio.resolver import AudioTrack, AudioResolver, UnsupportedSourceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ydl_class(info: dict) -> MagicMock:
    """Return a mock YoutubeDL class whose extract_info returns *info*."""
    mock_class = MagicMock()
    mock_ydl = mock_class.return_value.__enter__.return_value
    mock_ydl.extract_info.return_value = info
    return mock_class


def _youtube_info(
    title="Test Song",
    url="https://youtube.com/watch?v=abc",
    thumbnail="https://i.ytimg.com/vi/abc/default.jpg",
) -> dict:
    return {
        "title": title,
        "webpage_url": url,
        "url": "https://stream.example.com/audio.webm",
        "duration": 210,
        "thumbnail": thumbnail,
    }


def _search_info(title="Found Song") -> dict:
    """yt_dlp wraps search results in an 'entries' list."""
    return {
        "entries": [
            {
                "title": title,
                "webpage_url": "https://youtube.com/watch?v=xyz",
                "url": "https://stream.example.com/audio2.webm",
                "duration": 180,
            }
        ]
    }


# ---------------------------------------------------------------------------
# AudioTrack
# ---------------------------------------------------------------------------

class TestAudioTrack:
    def test_fields(self):
        track = AudioTrack(
            title="Song",
            url="https://example.com",
            stream_url="https://stream.example.com",
            duration=300,
            source="youtube",
        )
        assert track.title == "Song"
        assert track.url == "https://example.com"
        assert track.stream_url == "https://stream.example.com"
        assert track.duration == 300
        assert track.source == "youtube"
        assert track.thumbnail == ""

    def test_thumbnail_defaults_to_empty_string(self):
        track = AudioTrack(
            title="Song",
            url="https://example.com",
            stream_url="https://stream.example.com",
            duration=300,
            source="youtube",
        )
        assert track.thumbnail == ""

    def test_thumbnail_can_be_set(self):
        track = AudioTrack(
            title="Song",
            url="https://example.com",
            stream_url="https://stream.example.com",
            duration=300,
            source="youtube",
            thumbnail="https://i.ytimg.com/vi/abc/default.jpg",
        )
        assert track.thumbnail == "https://i.ytimg.com/vi/abc/default.jpg"


# ---------------------------------------------------------------------------
# AudioResolver – YouTube URL  (RED → will raise NotImplementedError)
# ---------------------------------------------------------------------------

class TestResolveYouTube:
    def test_youtube_com_url(self):
        mock_ytdl = _make_mock_ydl_class(_youtube_info())
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://www.youtube.com/watch?v=abc")
        assert isinstance(track, AudioTrack)
        assert track.title == "Test Song"
        assert track.stream_url == "https://stream.example.com/audio.webm"
        assert track.duration == 210
        assert track.source == "youtube"

    def test_youtu_be_short_url(self):
        mock_ytdl = _make_mock_ydl_class(_youtube_info(url="https://youtu.be/abc"))
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://youtu.be/abc")
        assert track.source == "youtube"
        assert track.title == "Test Song"

    def test_youtube_url_is_preserved(self):
        info = _youtube_info(url="https://www.youtube.com/watch?v=test123")
        mock_ytdl = _make_mock_ydl_class(info)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://www.youtube.com/watch?v=test123")
        assert track.url == "https://www.youtube.com/watch?v=test123"

    def test_thumbnail_populated_from_info(self):
        info = _youtube_info(thumbnail="https://i.ytimg.com/vi/abc/maxresdefault.jpg")
        mock_ytdl = _make_mock_ydl_class(info)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://www.youtube.com/watch?v=abc")
        assert track.thumbnail == "https://i.ytimg.com/vi/abc/maxresdefault.jpg"

    def test_thumbnail_defaults_to_empty_string_when_missing(self):
        info = {
            "title": "No Thumbnail",
            "webpage_url": "https://youtube.com/watch?v=abc",
            "url": "https://stream.example.com/audio.webm",
            "duration": 210,
            # 'thumbnail' key intentionally absent
        }
        mock_ytdl = _make_mock_ydl_class(info)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://www.youtube.com/watch?v=abc")
        assert track.thumbnail == ""


# ---------------------------------------------------------------------------
# AudioResolver – Spotify URL (now unsupported)
# ---------------------------------------------------------------------------

class TestResolveSpotify:
    def test_spotify_url_raises_unsupported_source_error(self):
        resolver = AudioResolver(ytdl_class=MagicMock())
        with pytest.raises(UnsupportedSourceError):
            resolver.resolve("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")

    def test_spotify_url_with_query_params_raises(self):
        resolver = AudioResolver(ytdl_class=MagicMock())
        with pytest.raises(UnsupportedSourceError):
            resolver.resolve("https://open.spotify.com/track/abc123?si=xyz")


# ---------------------------------------------------------------------------
# AudioResolver – SoundCloud URL
# ---------------------------------------------------------------------------

class TestResolveSoundCloud:
    def test_soundcloud_url(self):
        info = {
            "title": "SoundCloud Track",
            "webpage_url": "https://soundcloud.com/artist/track",
            "url": "https://stream.soundcloud.com/audio.mp3",
            "duration": 240,
        }
        mock_ytdl = _make_mock_ydl_class(info)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://soundcloud.com/artist/track")
        assert isinstance(track, AudioTrack)
        assert track.title == "SoundCloud Track"
        assert track.source == "soundcloud"
        assert track.duration == 240

    def test_soundcloud_www_url(self):
        info = {
            "title": "SC Track",
            "webpage_url": "https://www.soundcloud.com/artist/track",
            "url": "https://stream.soundcloud.com/audio.mp3",
            "duration": 120,
        }
        mock_ytdl = _make_mock_ydl_class(info)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://www.soundcloud.com/artist/track")
        assert track.source == "soundcloud"


# ---------------------------------------------------------------------------
# AudioResolver – plain search string
# ---------------------------------------------------------------------------

class TestResolveSearch:
    def test_plain_search_query(self):
        mock_ytdl = _make_mock_ydl_class(_search_info("Never Gonna Give You Up"))
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("never gonna give you up")
        assert isinstance(track, AudioTrack)
        assert track.title == "Never Gonna Give You Up"
        assert track.source == "search"

    def test_search_prefixes_ytsearch(self):
        mock_ytdl = _make_mock_ydl_class(_search_info())
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        resolver.resolve("some search query")
        mock_ydl = mock_ytdl.return_value.__enter__.return_value
        call_args = mock_ydl.extract_info.call_args[0][0]
        assert call_args.startswith("ytsearch1:")
        assert "some search query" in call_args

    def test_search_with_entries_returns_first_result(self):
        search_result = {
            "entries": [
                {
                    "title": "First Result",
                    "webpage_url": "https://youtube.com/watch?v=1",
                    "url": "https://stream.example.com/1.webm",
                    "duration": 180,
                },
                {
                    "title": "Second Result",
                    "webpage_url": "https://youtube.com/watch?v=2",
                    "url": "https://stream.example.com/2.webm",
                    "duration": 200,
                },
            ]
        }
        mock_ytdl = _make_mock_ydl_class(search_result)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("test query")
        assert track.title == "First Result"


# ---------------------------------------------------------------------------
# AudioResolver – unsupported URL
# ---------------------------------------------------------------------------

class TestResolveUnsupported:
    def test_unsupported_https_url_raises(self):
        resolver = AudioResolver(ytdl_class=MagicMock())
        with pytest.raises(UnsupportedSourceError):
            resolver.resolve("https://example.com/some/page")

    def test_unsupported_http_url_raises(self):
        resolver = AudioResolver(ytdl_class=MagicMock())
        with pytest.raises(UnsupportedSourceError):
            resolver.resolve("http://randomsite.org/music")

    def test_unsupported_error_message_contains_url(self):
        bad_url = "https://notadiscordmusicsite.com/track/123"
        resolver = AudioResolver(ytdl_class=MagicMock())
        with pytest.raises(UnsupportedSourceError, match=bad_url):
            resolver.resolve(bad_url)


# ---------------------------------------------------------------------------
# AudioResolver – duration defaults to 0 when missing from info
# ---------------------------------------------------------------------------

class TestResolveDurationFallback:
    def test_missing_duration_defaults_to_zero(self):
        info = {
            "title": "No Duration",
            "webpage_url": "https://youtube.com/watch?v=nodur",
            "url": "https://stream.example.com/audio.webm",
            # 'duration' key intentionally absent
        }
        mock_ytdl = _make_mock_ydl_class(info)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        track = resolver.resolve("https://www.youtube.com/watch?v=nodur")
        assert track.duration == 0


# ---------------------------------------------------------------------------
# AudioResolver – _get_ytdl_class lazy-import path
# ---------------------------------------------------------------------------

class TestGetYtdlClassLazyImport:
    def test_lazy_import_when_ytdl_class_not_provided(self):
        """When ytdl_class is None, resolver imports yt_dlp from sys.modules."""
        mock_ytdl_module = MagicMock()
        with patch.dict("sys.modules", {"yt_dlp": mock_ytdl_module}):
            resolver = AudioResolver()
            result = resolver._get_ytdl_class()
        assert result is mock_ytdl_module.YoutubeDL


# ---------------------------------------------------------------------------
# AudioResolver – search()
# ---------------------------------------------------------------------------


def _make_ydl_search_class(entries: list) -> MagicMock:
    """Return a mock YoutubeDL class that returns a multi-entry search result."""
    mock_class = MagicMock()
    mock_ydl = mock_class.return_value.__enter__.return_value
    mock_ydl.extract_info.return_value = {"entries": entries}
    return mock_class


def _make_entry(
    title="Track",
    webpage_url="https://youtube.com/watch?v=abc",
    duration=180,
    thumbnail="https://i.ytimg.com/vi/abc/default.jpg",
) -> dict:
    return {
        "title": title,
        "webpage_url": webpage_url,
        "url": "https://stream.example.com/audio.webm",
        "duration": duration,
        "thumbnail": thumbnail,
    }


class TestSearch:
    def test_returns_list_of_dicts(self):
        entries = [_make_entry("Song 1"), _make_entry("Song 2")]
        mock_ytdl = _make_ydl_search_class(entries)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        results = resolver.search("test query")
        assert isinstance(results, list)
        assert len(results) == 2

    def test_result_has_expected_fields(self):
        entry = _make_entry(
            title="Cool Song",
            webpage_url="https://youtube.com/watch?v=cool",
            duration=240,
            thumbnail="https://i.ytimg.com/vi/cool/default.jpg",
        )
        mock_ytdl = _make_ydl_search_class([entry])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        results = resolver.search("cool song")
        assert results[0] == {
            "title": "Cool Song",
            "url": "https://youtube.com/watch?v=cool",
            "duration": 240,
            "thumbnail": "https://i.ytimg.com/vi/cool/default.jpg",
        }

    def test_uses_ytsearch_prefix(self):
        mock_ytdl = _make_ydl_search_class([_make_entry()])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        resolver.search("my query", max_results=5)
        mock_ydl = mock_ytdl.return_value.__enter__.return_value
        call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == "ytsearch5:my query"

    def test_max_results_passed_to_prefix(self):
        mock_ytdl = _make_ydl_search_class([_make_entry()] * 10)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        resolver.search("query", max_results=10)
        mock_ydl = mock_ytdl.return_value.__enter__.return_value
        call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg.startswith("ytsearch10:")

    def test_empty_entries_returns_empty_list(self):
        mock_ytdl = _make_ydl_search_class([])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        results = resolver.search("no results query")
        assert results == []

    def test_none_info_returns_empty_list(self):
        mock_class = MagicMock()
        mock_ydl = mock_class.return_value.__enter__.return_value
        mock_ydl.extract_info.return_value = None
        resolver = AudioResolver(ytdl_class=mock_class)
        results = resolver.search("query")
        assert results == []

    def test_missing_optional_fields_use_defaults(self):
        entry = {"title": "Minimal", "webpage_url": "https://youtube.com/watch?v=m"}
        mock_ytdl = _make_ydl_search_class([entry])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        results = resolver.search("minimal")
        assert results[0]["duration"] == 0
        assert results[0]["thumbnail"] == ""


