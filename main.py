import discord

from bot.core.client import Client

client = Client(
                intents=discord.Intents.all(),
                allowed_mentions=discord.AllowedMentions(replied_user=False),
                proxy="http://127.0.0.1:2334"
                )


client.run()