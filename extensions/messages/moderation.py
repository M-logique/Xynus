from datetime import datetime, timezone
from re import compile, escape
from typing import Optional, Sequence

from discord import (AllowedMentions, Button, Interaction, Member, Message,
                     NotFound, User, app_commands)
from discord.ext import commands

from bot.core.client import Client
from bot.templates.cogs import Cog
from bot.templates.embeds import SimpleEmbed
from bot.templates.views import YesOrNoView
from bot.utils.config import Emojis
from bot.utils.functions import chunker

_emojis = Emojis()
checkmark = _emojis.get("checkmark")
crossmark = _emojis.get("crossmark")
exclamation = _emojis.get("exclamation")

class Moderation(Cog):

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.emoji = _emojis.get("shield")


    @commands.hybrid_command(
        name="ban", 
        aliases= ["b", "massban"],
        description="Mass bans members with two optional delete_days and reason parameters.",
    )
    @app_commands.describe(
        users = "Provide Member id or mention members with space",
        delete_days = "Provide days",
        reason = "Provide a reason"
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


        members = [*map(lambda x: x.id, ctx.guild.members)]
        
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
                failed_to_ban = f"\n{crossmark} | Failed to ban {', '.join(get_names(failed)[:5:])} {and_more(failed)}" if failed != [] else ""


                embed = SimpleEmbed(
                    self.client,
                    description=f"{checkmark} | Banned {', '.join(get_names(success)[:5:])} {and_more(success)}{failed_to_ban}"
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
            return await ctx.reply("Did not find any user that you can ban.")
    

        embed = SimpleEmbed(
            self.client,
            description=f"Are you sure that you want to ban these {len(users)} user(s)?"
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
    
    @commands.hybrid_command(
        name="unban", 
        aliases= ["ub"],
        description="Mass unbans members with an optional reason parameter.",
    )
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        users: commands.Greedy[User],
        *,
        reason: Optional[str] = "No reason provided"
    ):


        bans = [banned.user.id async for banned in ctx.guild.bans()]
        users = [*filter(lambda m: m.id in bans, users)]

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
                    await ctx.guild.unban(
                        user=user,
                        reason=reason,
                    )
                    success.append(user)
                except:
                    failed.append(user)
            else:
                and_more = lambda users: f"and {len(users) - 5} more" if len(users) > 5 else ""
                get_names = lambda users: [i.name for i in users]
                failed_to_ban = f"\n{crossmark} | Failed to unban {', '.join(get_names(failed)[:5:])} {and_more(failed)}" if failed != [] else ""


                embed = SimpleEmbed(
                    self.client,
                    description=f"{checkmark} | Unbanned {', '.join(get_names(success)[:5:])} {and_more(success)}{failed_to_ban}"
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
            return await ctx.reply("Did not find any user that you can unban.")
    

        embed = SimpleEmbed(
            self.client,
            description=f"Are you sure that you want to unban these {len(users)} user(s)?"
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
    
    
    
    @commands.hybrid_command(
            name="setnick",
            description="Change the nickname of a user.",
            aliases=["nick"]
    )
    @commands.has_permissions(
        manage_nicknames=True
    )
    @app_commands.describe(
        member = "Member to change nickname for.",
        nickname = "New nickname for the user."
    )
    @app_commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def setnick(
        self,
        ctx: commands.Context,
        member: Member,
        *,
        nickname: Optional[str] = None
    ):
        if member.top_role.position >= ctx.author.top_role.position \
            or member.top_role.position >= ctx.me.top_role.position:

            return await ctx.reply(
                f"{crossmark} | Unable to change nickname for {member.mention}",
                allowed_mentions=AllowedMentions(
                    users=False
                )
            )
        

        await member.edit(
            nick=nickname,
            reason=f"By {ctx.author} | {ctx.author.id}"
        )

        txt = ""

        if nickname:
            txt+=f"{checkmark} | Changed {member.mention}'s nickname to {nickname}."
        
        else:
            txt+=f"{checkmark} | {member.mention}'s nickname has been reset."

        await ctx.reply(
            txt,
            allowed_mentions=AllowedMentions(
                everyone=False,
                users=False,
                roles=False,
            )
        )


    
    @commands.hybrid_group(
        name="purge",
        fallback="all",
        description="Bulk deletes messages.",
        aliases=["clear"]
    )
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.describe(
        amount = "Enter a number between 2-1000 to bulk delete messages."
    )
    @app_commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.member)
    async def purge(
        self,
        ctx: commands.Context,
        amount: Optional[int] = 100,
    ):

        await ctx.defer()
        
        if amount > 1000 or amount < 2:
            return await ctx.reply(f"{crossmark} | You can only remove between 2 and 1000 messages.")

        messages = [message async for message in ctx.channel.history(limit=amount+1)]
        messages = [*filter(lambda msg: (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).days < 14, messages)]


        return await self._purge(
            messages=messages,
            ctx=ctx
        )



    @purge.command(
        name="before",
        description="Bulk deletes messages before the specified message.",
        with_app_command=True,
        aliases=["until"]

    )
    @app_commands.describe(
        message_id = "The ID of the message you want to delete before it."
    )
    async def purge_until(
        self,
        ctx: commands.Context,
        message_id: str,
    ):
        await ctx.defer()
        
        if not message_id.isnumeric(): 
            return await ctx.reply("Please enter the message id.")
        
        message_id = int(message_id)
        try:
            await ctx.channel.fetch_message(message_id)
        except NotFound:
            return await ctx.reply(f"{crossmark} Did not find the specified message.")
        
        messages = [message async for message in ctx.channel.history(limit=500)]
        messages = [*filter(lambda msg: (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).days < 14 and (msg.id > message_id), messages)]


        return await self._purge(
            messages=messages,
            ctx=ctx
        )


    @purge.command(
        name="bots",
        description="Bulk deletes messages that sent by bots.",
        with_app_command=True

    )
    @app_commands.describe(
        amount = "Enter a number between 2-1000 to bulk delete messages."
    )
    async def purge_bots(
        self,
        ctx: commands.Context,
        amount: Optional[int] = 100,
    ):
        await ctx.defer()
        
        if amount > 1000 or amount < 2:
            return await ctx.reply(f"{crossmark} | You can only remove between 2 and 1000 messages.")

        messages = [message async for message in ctx.channel.history(limit=amount+1)]
        messages = [*filter(lambda msg: (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).days < 14 and msg.author.bot, messages)]


        return await self._purge(
            messages=messages,
            ctx=ctx
        )


    @purge.command(
        name="commands",
        description="Deletes the bulk of messages that contain a command.",
        with_app_command=True,
        aliases=["cmds"]
    )
    @app_commands.describe(
        prefix = "The prefix of the commands you want to delete."
    )
    async def purge_commands(
        self,
        ctx: commands.Context,
        *,
        prefix: str,
    ):
        await ctx.defer()

        is_command = lambda message: bool(compile(rf'^{escape(prefix)}\w+').match(message))

        messages = [message async for message in ctx.channel.history(limit=500)]
        messages = [*filter(lambda msg: (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).days < 14 and (not msg.author.bot and is_command(msg.content)), messages)]

        return await self._purge(
            messages=messages,
            ctx=ctx
        )

    @purge.command(
        name="user",
        description="Deletes the bulk of messages that sent by a user.",
        with_app_command=True
    )
    @app_commands.describe(
        user = "Please enter the user.",
        amount = "Enter a number between 2-1000 to bulk delete messages."
    )
    async def purge_user(
        self,
        ctx: commands.Context,
        user: User,
        amount: Optional[int] = 300
    ):

        if amount > 1000 or amount < 2:
            return await ctx.reply(f"{crossmark} | You can only remove between 2 and 1000 messages.")        


        await ctx.defer()

        messages = [message async for message in ctx.channel.history(limit=amount)]
        messages = [*filter(lambda msg: (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).days < 14 and msg.author.id == user.id, messages)]

        return await self._purge(
            messages=messages,
            ctx=ctx
        )


    @purge.command(
        name="embeds",
        description="Deletes the bulk of messages that has an embed.",
        with_app_command=True
    )
    @app_commands.describe(
        amount = "Enter a number between 2-1000 to bulk delete messages.",
        only_bots = "if enabled, will only delete the messages of bots."
    )
    async def purge_embeds(
        self,
        ctx: commands.Context,
        amount: Optional[int] = 100,
        only_bots: Optional[bool] = True
    ):
        await ctx.defer()

        check_bots = lambda user: True if not only_bots else  user.bot

        if amount > 1000 or amount < 2:
            return await ctx.reply(f"{crossmark} | You can only remove between 2 and 1000 messages.")


        messages = [message async for message in ctx.channel.history(limit=amount)]
        messages = [*filter(lambda msg: (datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc)).days < 14 and len(msg.embeds) != 0 and check_bots(msg.author), messages)]

        return await self._purge(
            messages=messages,
            ctx=ctx
        )


    async def _purge(
            self,
            messages: Sequence[Message],
            ctx: commands.Context
    ):
        

        total_messages = len(messages)

        chunks = chunker(messages, 100)

        msg = await ctx.reply(f"{exclamation} | Started removing {total_messages} messages.")

        for chunk in chunks:
            await ctx.channel.delete_messages(chunk)
        try:
            await msg.edit(content=f"{checkmark} | Removed {total_messages} messages.")
            await msg.delete(delay=5)
        except:
            pass



async def setup(c): await c.add_cog(Moderation(c))