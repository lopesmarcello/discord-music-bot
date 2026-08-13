"""Bot lifecycle tests."""

import subprocess
import sys
from textwrap import dedent


def test_global_commands_sync_once_after_cog_setup():
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "ignore::DeprecationWarning",
            "-c",
            dedent(
                """
                import asyncio
                from types import SimpleNamespace

                from bot.bot import create_bot


                async def run():
                    bot = create_bot()
                    sync_calls = []
                    phase = "setup"

                    async def sync(*, guild=None):
                        sync_calls.append(
                            (phase, guild, bot.get_cog("Music") is not None)
                        )
                        return []

                    bot.tree.sync = sync
                    bot._connection.user = SimpleNamespace(id=123)
                    bot._connection._guilds = {123: SimpleNamespace(id=123)}

                    try:
                        await bot.setup_hook()
                        phase = "ready"
                        await bot.on_ready()
                    finally:
                        await bot.close()

                    assert sync_calls == [("setup", None, True)], sync_calls


                asyncio.run(run())
                """
            ),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
