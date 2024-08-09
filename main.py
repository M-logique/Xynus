from discord import AllowedMentions, Intents

from bot.core.client import Client

client = Client(
    intents=Intents.all(),
    allowed_mentions=AllowedMentions(
        replied_user=False
    )
)


client.run()
