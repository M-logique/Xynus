from typing import Optional

from discord import Button, Interaction, User
from discord.ext import commands

from bot.core import guilds
from bot.core.client import Client
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import Cog
from bot.utils.config import Emojis
from bot.utils.functions import parse_time

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
        users: commands.Greedy[User],
        delete_days: Optional[int] = 7,
        *,
        reason: Optional[str] = "No reason provided"
    ):

        members = [i.id for i in ctx.guild.members]
        
        users = [*filter(lambda m: not m.id in members or ((ctx.guild.get_member(m.id).top_role < ctx.author.top_role and m.id != ctx.guild.owner_id) or ctx.guild.owner_id == ctx.author.id ), users)]

        reason = f"By {ctx.author.id}: " + reason

        async def yes_button(
                interaction: Interaction,
                button: Button
        ) -> None:
            success = []
            failed = []
            for user in users:

                try:
                    await ctx.guild.ban(
                        reason=reason,
                        delete_message_days=delete_days,
                    )
                    success.append(user)
                except:
                    failed.append(user)
        
    
    
async def setup(c): await c.add_cog(Moderation(c))