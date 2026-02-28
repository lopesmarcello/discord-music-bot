"""Entry point for the Discord music bot."""
import asyncio
import os

from dotenv import load_dotenv

from bot.bot import create_bot


async def _run(token: str) -> None:
    port = int(os.getenv("API_PORT", "8080"))
    bot = create_bot()

    from bot.api.server import create_app, start_api_server  # noqa: PLC0415

    app = create_app()
    runner = await start_api_server(app, "0.0.0.0", port)
    try:
        async with bot:
            await bot.start(token)
    finally:
        await runner.cleanup()


def main() -> None:
    load_dotenv()
    token = os.environ["DISCORD_TOKEN"]
    asyncio.run(_run(token))


if __name__ == "__main__":
    main()
