"""Unit tests for AudioResolver."""
from __future__ import annotations

import io
import json
import os

import pytest
from unittest.mock import MagicMock, patch

from bot.audio.resolver import (
    AudioTrack,
    AudioResolver,
    UnsupportedSourceError,
    _parse_iso8601_duration,
)


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


# ---------------------------------------------------------------------------
# _parse_iso8601_duration helper
# ---------------------------------------------------------------------------


class TestParseIso8601Duration:
    def test_minutes_and_seconds(self):
        assert _parse_iso8601_duration("PT3M45S") == 225

    def test_hours_minutes_seconds(self):
        assert _parse_iso8601_duration("PT1H2M3S") == 3723

    def test_seconds_only(self):
        assert _parse_iso8601_duration("PT30S") == 30

    def test_minutes_only(self):
        assert _parse_iso8601_duration("PT5M") == 300

    def test_hours_only(self):
        assert _parse_iso8601_duration("PT2H") == 7200

    def test_invalid_returns_zero(self):
        assert _parse_iso8601_duration("invalid") == 0


# ---------------------------------------------------------------------------
# AudioResolver – search() SoundCloud fallback (no YOUTUBE_API_KEY)
# ---------------------------------------------------------------------------


class TestSearch:
    """Tests for search() with no YOUTUBE_API_KEY set (SoundCloud fallback)."""

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
            webpage_url="https://soundcloud.com/artist/cool-song",
            duration=240,
            thumbnail="https://i1.sndcdn.com/artworks/cool.jpg",
        )
        mock_ytdl = _make_ydl_search_class([entry])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        results = resolver.search("cool song")
        assert results[0] == {
            "title": "Cool Song",
            "url": "https://soundcloud.com/artist/cool-song",
            "duration": 240,
            "thumbnail": "https://i1.sndcdn.com/artworks/cool.jpg",
        }

    def test_uses_scsearch_prefix(self):
        mock_ytdl = _make_ydl_search_class([_make_entry()])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        resolver.search("my query", max_results=5)
        mock_ydl = mock_ytdl.return_value.__enter__.return_value
        call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == "scsearch5:my query"

    def test_max_results_passed_to_prefix(self):
        mock_ytdl = _make_ydl_search_class([_make_entry()] * 10)
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        resolver.search("query", max_results=10)
        mock_ydl = mock_ytdl.return_value.__enter__.return_value
        call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg.startswith("scsearch10:")

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
        entry = {"title": "Minimal", "webpage_url": "https://soundcloud.com/x/y"}
        mock_ytdl = _make_ydl_search_class([entry])
        resolver = AudioResolver(ytdl_class=mock_ytdl)
        results = resolver.search("minimal")
        assert results[0]["duration"] == 0
        assert results[0]["thumbnail"] == ""


# ---------------------------------------------------------------------------
# AudioResolver – search() via YouTube Data API v3
# ---------------------------------------------------------------------------


def _make_http_get_fn(responses: list[dict]) -> MagicMock:
    """Return a mock _http_get_fn that yields successive JSON responses."""
    call_count = [0]

    class FakeResp:
        def __init__(self, data):
            self._data = json.dumps(data).encode()

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def http_get(url):
        idx = call_count[0]
        call_count[0] += 1
        return FakeResp(responses[idx])

    return http_get


def _yt_search_response(video_ids: list[str]) -> dict:
    """Fake YouTube /search response."""
    return {
        "items": [
            {
                "id": {"videoId": vid_id},
                "snippet": {
                    "title": f"Title {vid_id}",
                    "thumbnails": {
                        "high": {"url": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"}
                    },
                },
            }
            for vid_id in video_ids
        ]
    }


def _yt_videos_response(video_ids: list[str], duration="PT3M30S") -> dict:
    """Fake YouTube /videos?part=contentDetails response."""
    return {
        "items": [
            {"id": vid_id, "contentDetails": {"duration": duration}}
            for vid_id in video_ids
        ]
    }


class TestSearchYouTubeApi:
    """Tests for search() when YOUTUBE_API_KEY is set."""

    def test_uses_youtube_api_when_key_set(self):
        video_ids = ["abc123"]
        http_fn = _make_http_get_fn([
            _yt_search_response(video_ids),
            _yt_videos_response(video_ids, "PT2M30S"),
        ])
        resolver = AudioResolver(_http_get_fn=http_fn)
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-key"}):
            results = resolver.search("test query")
        assert len(results) == 1
        assert results[0]["title"] == "Title abc123"
        assert results[0]["url"] == "https://www.youtube.com/watch?v=abc123"
        assert results[0]["duration"] == 150  # 2*60+30
        assert results[0]["thumbnail"] == "https://i.ytimg.com/vi/abc123/hqdefault.jpg"

    def test_multiple_results(self):
        video_ids = ["v1", "v2", "v3"]
        http_fn = _make_http_get_fn([
            _yt_search_response(video_ids),
            _yt_videos_response(video_ids, "PT1M0S"),
        ])
        resolver = AudioResolver(_http_get_fn=http_fn)
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "key"}):
            results = resolver.search("query", max_results=3)
        assert len(results) == 3
        assert results[1]["url"] == "https://www.youtube.com/watch?v=v2"

    def test_empty_search_response_returns_empty_list(self):
        http_fn = _make_http_get_fn([{"items": []}])
        resolver = AudioResolver(_http_get_fn=http_fn)
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "key"}):
            results = resolver.search("nothing here")
        assert results == []

    def test_falls_back_to_soundcloud_when_youtube_api_raises(self):
        """If the YouTube API call raises an exception, fall back to SoundCloud."""
        def bad_http_fn(url):
            raise OSError("network error")

        entries = [_make_entry("SC Track", webpage_url="https://soundcloud.com/x/y")]
        mock_ytdl = _make_ydl_search_class(entries)
        resolver = AudioResolver(ytdl_class=mock_ytdl, _http_get_fn=bad_http_fn)
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "key"}):
            results = resolver.search("test")
        assert len(results) == 1
        assert results[0]["title"] == "SC Track"


