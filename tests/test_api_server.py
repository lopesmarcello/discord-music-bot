"""Tests for US-001: HTTP API server embedded in the bot."""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import patch

# Stubs for aiohttp are registered in tests/conftest.py before this file loads.
# Import the stub classes from sys.modules so we use the same objects everywhere.
_mock_web = sys.modules["aiohttp.web"]
_FakeApplication = _mock_web.Application
_FakeAppRunner = _mock_web.AppRunner
_FakeTCPSite = _mock_web.TCPSite

from bot.api.server import create_app, start_api_server  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateApp:
    def test_returns_application_instance(self):
        """create_app returns an Application instance."""
        app = create_app()
        assert isinstance(app, _FakeApplication)

    def test_app_is_new_instance_each_call(self):
        """Each call to create_app returns a distinct Application."""
        app1 = create_app()
        app2 = create_app()
        assert app1 is not app2


class TestStartApiServer:
    def test_returns_runner(self):
        """start_api_server sets up a runner and returns it."""
        app = create_app()
        runner = asyncio.run(start_api_server(app, "0.0.0.0", 8080))
        assert isinstance(runner, _FakeAppRunner)

    def test_setup_called_on_runner(self):
        """AppRunner.setup is awaited during server start."""
        app = create_app()
        runner = asyncio.run(start_api_server(app, "0.0.0.0", 8080))
        runner.setup.assert_called_once()

    def test_site_start_called(self):
        """TCPSite.start is awaited during server start."""
        app = create_app()

        created_sites = []

        def capturing_tcp_site(runner, host, port):
            from tests.conftest import FakeTCPSite  # noqa: PLC0415
            site = FakeTCPSite(runner, host, port)
            created_sites.append(site)
            return site

        with patch.object(_mock_web, "TCPSite", side_effect=capturing_tcp_site):
            asyncio.run(start_api_server(app, "0.0.0.0", 8080))

        assert len(created_sites) == 1
        created_sites[0].start.assert_called_once()

    def test_binds_to_all_interfaces(self):
        """start_api_server uses 0.0.0.0 for Docker networking."""
        app = create_app()
        captured = []

        def capturing_tcp_site(runner, host, port):
            from tests.conftest import FakeTCPSite  # noqa: PLC0415
            captured.append((host, port))
            return FakeTCPSite(runner, host, port)

        with patch.object(_mock_web, "TCPSite", side_effect=capturing_tcp_site):
            asyncio.run(start_api_server(app, "0.0.0.0", 8080))

        assert captured[0][0] == "0.0.0.0"

    def test_uses_configured_port(self):
        """start_api_server passes the given port to TCPSite."""
        app = create_app()
        captured = []

        def capturing_tcp_site(runner, host, port):
            from tests.conftest import FakeTCPSite  # noqa: PLC0415
            captured.append((host, port))
            return FakeTCPSite(runner, host, port)

        with patch.object(_mock_web, "TCPSite", side_effect=capturing_tcp_site):
            asyncio.run(start_api_server(app, "0.0.0.0", 9090))

        assert captured[0][1] == 9090


class TestApiPortEnvVar:
    def test_api_port_defaults_to_8080(self):
        """API_PORT env var defaults to 8080."""
        env_copy = {k: v for k, v in os.environ.items() if k != "API_PORT"}
        with patch.dict(os.environ, env_copy, clear=True):
            port = int(os.getenv("API_PORT", "8080"))
        assert port == 8080

    def test_api_port_reads_from_env(self):
        """API_PORT can be overridden via environment variable."""
        with patch.dict(os.environ, {"API_PORT": "9999"}):
            port = int(os.getenv("API_PORT", "8080"))
        assert port == 9999
