from discord import AllowedMentions, Intents

from bot.core.client import Xynus

client = Xynus(
    intents=Intents.all(),
    allowed_mentions=AllowedMentions(
        replied_user=False
    )
)


client.run()
