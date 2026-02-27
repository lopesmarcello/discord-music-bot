"""Conftest for integration tests: mock discord before cog imports."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Stub discord classes needed by the Music cog
# ---------------------------------------------------------------------------

class _FakeCog:
    """Minimal Cog base class stub."""


class _FakeContext:
    """Minimal Context stub."""


def _fake_hybrid_command(*args, **kwargs):
    """Decorator stub that passes the function through unchanged."""
    def decorator(func):
        return func
    return decorator


# Build mock modules
_mock_commands = MagicMock()
_mock_commands.Cog = _FakeCog
_mock_commands.Context = _FakeContext
_mock_commands.hybrid_command = _fake_hybrid_command

_mock_discord_ext = MagicMock()
_mock_discord_ext.commands = _mock_commands

_mock_discord = MagicMock()
_mock_discord.ext = _mock_discord_ext

# Register in sys.modules before any test module imports bot code
sys.modules.setdefault("discord", _mock_discord)
sys.modules.setdefault("discord.ext", _mock_discord_ext)
sys.modules.setdefault("discord.ext.commands", _mock_commands)
