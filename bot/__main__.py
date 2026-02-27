"""Entry point for the Discord music bot."""
import os

from dotenv import load_dotenv

from bot.bot import create_bot


def main() -> None:
    load_dotenv()
    token = os.environ["DISCORD_TOKEN"]
    bot = create_bot()
    bot.run(token)


if __name__ == "__main__":
    main()
