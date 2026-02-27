"""Unit tests for AudioResolver (US-002)."""
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


def _youtube_info(title="Test Song", url="https://youtube.com/watch?v=abc") -> dict:
    return {
        "title": title,
        "webpage_url": url,
        "url": "https://stream.example.com/audio.webm",
        "duration": 210,
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


# ---------------------------------------------------------------------------
# AudioResolver – Spotify URL
# ---------------------------------------------------------------------------

class TestResolveSpotify:
    def _make_resolver(self, search_info=None):
        """Return a resolver with mocked ytdl (for search) and spotipy."""
        if search_info is None:
            search_info = _search_info("Artist - Title")
        mock_ytdl = _make_mock_ydl_class(search_info)

        mock_sp = MagicMock()
        mock_sp.track.return_value = {
            "name": "Never Gonna Give You Up",
            "artists": [{"name": "Rick Astley"}],
        }
        return AudioResolver(ytdl_class=mock_ytdl, spotipy_client=mock_sp), mock_sp

    def test_spotify_url_returns_audio_track(self):
        resolver, _ = self._make_resolver()
        track = resolver.resolve("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        assert isinstance(track, AudioTrack)
        assert track.source == "spotify"

    def test_spotify_url_is_preserved(self):
        spotify_url = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        resolver, _ = self._make_resolver()
        track = resolver.resolve(spotify_url)
        assert track.url == spotify_url

    def test_spotify_fetches_metadata_from_spotipy(self):
        resolver, mock_sp = self._make_resolver()
        resolver.resolve("https://open.spotify.com/track/abc123")
        mock_sp.track.assert_called_once_with("abc123")

    def test_spotify_builds_search_query_from_metadata(self):
        mock_ytdl = _make_mock_ydl_class(_search_info())
        mock_sp = MagicMock()
        mock_sp.track.return_value = {
            "name": "Never Gonna Give You Up",
            "artists": [{"name": "Rick Astley"}],
        }
        resolver = AudioResolver(ytdl_class=mock_ytdl, spotipy_client=mock_sp)
        resolver.resolve("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        # extract_info should have been called with a search query
        mock_ydl = mock_ytdl.return_value.__enter__.return_value
        call_args = mock_ydl.extract_info.call_args
        search_arg = call_args[0][0]
        assert "Rick Astley" in search_arg
        assert "Never Gonna Give You Up" in search_arg

    def test_spotify_url_with_query_params_stripped(self):
        spotify_url = "https://open.spotify.com/track/abc123?si=xyz"
        resolver, mock_sp = self._make_resolver()
        resolver.resolve(spotify_url)
        mock_sp.track.assert_called_once_with("abc123")


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
# AudioResolver – _get_spotipy_client lazy-import path
# ---------------------------------------------------------------------------

class TestGetSpotipyClientLazyImport:
    def test_lazy_import_when_spotipy_client_not_provided(self):
        """When spotipy_client is None, resolver imports spotipy from sys.modules."""
        mock_spotipy_module = MagicMock()
        mock_oauth2_module = MagicMock()
        with patch.dict(
            "sys.modules",
            {"spotipy": mock_spotipy_module, "spotipy.oauth2": mock_oauth2_module},
        ):
            resolver = AudioResolver()
            client = resolver._get_spotipy_client()
        assert client is mock_spotipy_module.Spotify.return_value
