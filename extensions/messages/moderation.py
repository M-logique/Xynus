from typing import Optional

from discord import Member
from discord.ext import commands

from bot.core import guilds
from bot.core.client import Client
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import Cog
from bot.utils.config import Emojis

_emojis = Emojis()

class Moderation(Cog):

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.emoji = _emojis.global_emojis["shield"]


    @commands.hybrid_command(
        name="ban", 
        aliases= ["b", "massban"],
        description="Mass bans members with an optional delete_days and reason parameter",
        usage="<Member> [delete_days] [reason]",
        parent="moderation"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member],
        reason: Optional[str] = "No reason provided"
    ):
        
        members = [*filter(lambda m: m.top_role < ctx.author.top_role or ctx.guild.owner_id == ctx.author.id, members)]

        
    
    
async def setup(c): await c.add_cog(Moderation(c))