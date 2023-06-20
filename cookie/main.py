import asyncio
import logging
import os

import openai
from dotenv import load_dotenv

from cookie import discord_bot
from cookie.user_store import UserStore

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    del os.environ["NTROPY_API_KEY"]
    load_dotenv()
    openai.api_key = os.environ["OPENAI_API_KEY"]

    asyncio.run(
        discord_bot.client.start(
            os.environ["DISCORD_TOKEN"], UserStore(), os.environ["DISCORD_GUILD_ID"]
        )
    )
