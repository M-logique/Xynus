import discord

from bot.core.client import Client

client = Client(
                intents=discord.Intents.all(),
                allowed_mentions=discord.AllowedMentions(replied_user=False),
                )


client.run()