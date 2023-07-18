# Ntropy Cookie

A financial assistant using LLMs and Ntropy transaction enrichment.

This code accompanies our blog post [The new pursuit for a Mint alternative: powered by AI](http://ntropy.com/post/pursuit-for-a-mint-alternative-powered-by-ai?utm_content=c0d4&utm_source=github).

## How to run

1. Copy `.env.example` to `.env` and fill in

- DISCORD_TOKEN: Secret token for your discord bot, get one and more info on how to develop Discord bots [here](https://discord.com/developers/docs/getting-started)
- DISCORD_GUILD_ID: Your discord server id
- OPENAI_API_KEY: Your OpenAI api key
- NTROPY_API_KEY: Your Ntropy API key, get one [here](https://dashboard.ntropy.com/)

2. Install [Poetry](https://python-poetry.org/) and run `poetry install`
3. Run `poetry run python -m cookie.main` to start the bot

## Using the bot

1. Open direct message with your bot
2. Upload a csv with `/hello_csv`. The csv format:
   ```csv
   date,description,entry_type,amount,iso_currency_code,account_holder_id,account_holder_type
   2023-01-24,Transaction description,credit,123,USD,demo-ah,consumer
   ...
   ```
3. Use `/prompt <text>` for free-form questions, or one of the premade commands like `/savings_opportunities`
4. When you ran a command, you can also chat with the bot directly, eg. to ask it to correct itself. The context resets whenever you run a new command.
5. Use `/forget` to unlink your transactions, you can then use `/hello_csv` again as in step 2.
