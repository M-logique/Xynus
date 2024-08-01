from typing import Optional

from discord import Button, Interaction, User
from discord.ext import commands

from bot.core import guilds
from bot.core.client import Client
from bot.templates.buttons import DeleteButton
from bot.templates.views import YesOrNoView
from bot.templates.cogs import Cog
from bot.utils.config import Emojis
from bot.templates.embeds import SimpleEmbed
from discord import app_commands
from bot.utils.functions import chunker
from datetime import datetime, UTC

_emojis = Emojis()

class Moderation(Cog):

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.emoji = _emojis.global_emojis["shield"]


    @commands.hybrid_command(
        name="ban", 
        aliases= ["b", "massban"],
        description="Mass bans members with an optional delete_days and reason parameter.",
    )

    @commands.has_permissions(ban_members=True)
    @app_commands.guilds(*guilds)
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
            await interaction.response.edit_message()
            await interaction.delete_original_response()
            success = []
            failed = []
            for user in users:

                try:
                    await ctx.guild.ban(
                        user=user,
                        reason=reason,
                        delete_message_days=delete_days,
                    )
                    success.append(user)
                except:
                    failed.append(user)
            else:
                and_more = lambda users: f"and {len(users) - 5} more" if len(users) > 5 else ""
                get_names = lambda users: [i.name for i in users]
                failed_to_ban = f"\n{_emojis.global_emojis.get('crossmark')} | Failed to ban {', '.join(get_names(failed)[:5:])} {and_more(failed)}" if failed != [] else ""


                embed = SimpleEmbed(
                    self.client,
                    description=f"{_emojis.global_emojis.get('checkmark')} | Banned {', '.join(get_names(success)[:5:])} {and_more(success)}{failed_to_ban}"
                )
                embed.set_footer(
                    text=f"Invoked by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar
                )

                await interaction.channel.send(
                    embed=embed,   
                )
        

        async def no_button(
                interaction: Interaction,
                button: Button
        ):
            await interaction.response.edit_message()
            await interaction.delete_original_response()

        
        if len(users) == 0:
            return await ctx.reply("Did not find any user that you can ban")
    

        embed = SimpleEmbed(
            self.client,
            description=f"Are you sure that you want to ban these {len(users)} users?"
        )

        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar
        )

        await ctx.reply(
            embed=embed,
            view=YesOrNoView(
                function_to_call_after_yes=yes_button,
                function_to_call_after_no=no_button,
                author=ctx.author
            )
        )
    
    @commands.hybrid_group(
        name="purge",
        fallback="all",
        description="Bulk deletes messages"
    )
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.guilds(*guilds)
    async def purge(
        self,
        ctx: commands.Context,
        amount: Optional[int] = 100,
    ):
        if amount > 1000 or amount < 2:
            return await ctx.reply(f"{_emojis.global_emojis['crossmark']} You can only remove between 2 and 1000 messages.")

        messages = [message async for message in ctx.channel.history(limit=amount+1)]
        messages = [*filter(lambda msg: (datetime.now(UTC) - msg.created_at).days < 14, messages)]


        chunks = chunker(messages, 100)

        msg = await ctx.reply(f"{_emojis.global_emojis['exclamation']} Started removing {amount} messages.")

        for chunk in chunks:
            await ctx.channel.delete_messages(chunk)
        try:
            await msg.edit(content=f"{_emojis.global_emojis['checkmark']} Removed {amount} messages.")
            await msg.delete(delay=5)
        except:
            pass

async def setup(c): await c.add_cog(Moderation(c))