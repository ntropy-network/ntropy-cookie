import asyncio
import io
import json
import logging
from csv import DictReader
from datetime import date
from functools import partial

import discord
from more_itertools import chunked

from cookie.get_transactions import get_transactions
from cookie.ntropy import enrich
from cookie.openai import ChatSession
from cookie.prompts import prompt_commands
from cookie.transaction_formatting import (
    prompt_format_transactions,
    table_format_transactions,
)
from cookie.transactions import EnrichedTransaction, UnregisteredUser
from cookie.user_store import User, UserStore

logger = logging.getLogger(__file__)


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, **options) -> None:
        super().__init__(intents=intents, **options)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        assert self.user is not None
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message):
        if self.user is None or message.author.id == self.user.id:
            return

        if isinstance(message.channel, discord.DMChannel):
            temp_message = await message.author.send(":thinking:")
            user = self.user_store.get_user_from_discord(message.author)
            if user is not None:
                chat_session = self.get_user_chat_session(user)
                if chat_session.messages:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        partial(chat_session.respond, message.content),
                    )
                    await temp_message.edit(content=response)

    async def setup_hook(self):
        logger.info("Sync global command tree")
        await self.tree.sync()
        logger.info("Sync guild command tree")
        guild = discord.Object(self.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info("Sync command tree done")

    async def start(self, token: str, user_store: UserStore, guild_id: str):
        self.user_store = user_store
        self.guild_id = guild_id
        user_chat_sessions = {}

        def get_user_chat_session(user: User) -> ChatSession:
            if user.id not in user_chat_sessions:
                user_chat_sessions[user.id] = ChatSession(model="gpt-4")
            return user_chat_sessions[user.id]

        self.get_user_chat_session = get_user_chat_session
        return await super().start(token)


intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True


client = MyClient(intents=intents)


@client.tree.command()
async def hello_csv(
    interaction: discord.Interaction[MyClient], csv: discord.Attachment
):
    try:
        contents = io.BytesIO(await csv.read())
    except discord.DiscordException:
        await interaction.response.send_message("Failed to download csv")
        return

    reader = DictReader(io.TextIOWrapper(contents))
    txs = list(reader)
    missing = {"date", "description", "amount", "iso_currency_code", "entry_type"} - (
        set(reader.fieldnames) if reader.fieldnames else set()
    )
    if len(missing):
        await interaction.response.send_message(f"Missing fields {', '.join(missing)}")
        return

    for i, tx in enumerate(txs):
        try:
            date.fromisoformat(tx["date"])
        except ValueError as e:
            await interaction.response.send_message(
                f"Invalid date on row {i+2}: {e.args}"
            )
            return
        try:
            amount_sign = 1 if tx["entry_type"] in ["credit", "incoming"] else -1
            tx["amount"] = float(tx["amount"]) * amount_sign
        except ValueError as e:
            await interaction.response.send_message(
                f"Invalid amount on row {i+2}: {tx['amount']}"
            )
            return

    users = interaction.client.user_store
    user = users.get_user_from_discord(interaction.user)
    if user is None:
        user = users.create_user(interaction.user.id)

    user.cached_txs_json = json.dumps(txs)
    users.update_user(user)
    await interaction.response.send_message(f"Imported {len(txs)} transactions")


async def get_enriched_recent_transactions(
    user_store: UserStore, user: User, n: int = 20
) -> list[EnrichedTransaction]:
    transactions = await asyncio.get_event_loop().run_in_executor(
        None, partial(get_transactions, user=user, n=n)
    )

    return await asyncio.get_event_loop().run_in_executor(None, enrich, transactions)


@client.tree.command()
async def transactions(
    interaction: discord.Interaction[MyClient], num_transactions: int = 10
) -> None:
    users: UserStore = interaction.client.user_store
    user = users.get_user_from_discord(interaction.user)

    try:
        if user is None:
            raise UnregisteredUser()

        await interaction.response.defer()

        transactions = await get_enriched_recent_transactions(
            users, user, n=num_transactions
        )

        for transaction_batch in chunked(transactions, n=5):
            table = table_format_transactions(transaction_batch)

            dm_channel = await interaction.user.create_dm()
            table_message = f"```\n{table}\n```"
            await dm_channel.send(table_message)

        await interaction.followup.send("..")
    except UnregisteredUser:
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send("Upload your transactions first by running /hello_csv")
        await interaction.followup.send("..")


@client.tree.command()
async def prompt(interaction: discord.Interaction[MyClient], prompt: str) -> None:
    await prompt_and_respond(
        interaction=interaction, prompt=prompt, header=f"**Prompt**: {prompt}\n"
    )


def make_prompt_command(command_name, prompt_text):
    async def prompt_command(interaction: discord.Interaction):
        await prompt_and_respond(
            interaction=interaction,
            prompt=prompt_text,
            header=f"**{command_name}**\n",
        )

    return prompt_command


for command_name, prompt_text in prompt_commands.items():
    client.tree.command(name=command_name)(
        make_prompt_command(command_name, prompt_text)
    )


async def prompt_and_respond(
    interaction: discord.Interaction[MyClient], prompt: str, header: str
):
    await interaction.response.defer()

    users: UserStore = interaction.client.user_store
    user = users.get_user_from_discord(interaction.user)

    try:
        if user is None:
            raise UnregisteredUser()
        transactions = await get_enriched_recent_transactions(users, user, n=300)
    except UnregisteredUser:
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send("Upload your transactions first by running /hello_csv")
        return

    logger.info("Building txs csv")
    transaction_csv = prompt_format_transactions(transactions)

    system_prompt = (
        f"You are transaction-gpt and today is {date.today()}. "
        "Answer the user's prompts in up to 100 words for the bank transactions "
        "given below as if you are speaking to the account holder. "
        "Your message will be used in a Discord chat so you can use Discord's "
        "markdown format for emphasis. "
        f"\n\n{transaction_csv}"
    )

    user_chat_session: ChatSession = interaction.client.get_user_chat_session(user)
    user_chat_session.setup(system_prompt=system_prompt)

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        partial(user_chat_session.respond, prompt),
    )
    logger.info("Got openai response")

    dm_channel = await interaction.user.create_dm()
    await dm_channel.send(f"{header}{response}")

    await interaction.followup.send("...")

    logger.info("Done")


@client.tree.command()
async def forget(interaction: discord.Interaction[MyClient]):
    users: UserStore = interaction.client.user_store
    user = users.get_user_from_discord(interaction.user)
    if user is None:
        await interaction.response.send_message("User not found")
        return

    users.delete_user(user)
    await interaction.response.send_message("Success")


@client.tree.command()
async def expire_txs(interaction: discord.Interaction[MyClient]):
    users: UserStore = interaction.client.user_store
    user = users.get_user_from_discord(interaction.user)
    if user is None:
        await interaction.response.send_message("User not found")
        return

    user.cached_txs_json = None
    users.update_user(user)
    await interaction.response.send_message("Success")
