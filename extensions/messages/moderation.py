from datetime import datetime, timezone
from re import compile, escape
from typing import TYPE_CHECKING, Optional, Sequence

from discord import (AllowedMentions, Member, Message, NotFound, User,
                     app_commands)
from discord.ext import commands

from bot.templates.cogs import XynusCog
from bot.templates.embeds import SimpleEmbed
from bot.utils.config import Emojis
from bot.utils.functions import chunker

if TYPE_CHECKING:
    from bot.templates.context import XynusContext

_emojis = Emojis()
checkmark = _emojis.get("checkmark")
crossmark = _emojis.get("crossmark")
exclamation = _emojis.get("exclamation")

class Moderation(XynusCog, emoji=_emojis.get("shield")):

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
        ctx: "XynusContext",
        users: commands.Greedy[User],
        delete_days: Optional[int] = 7,
        *,
        reason: Optional[str] = "No reason provided"
    ):


        members = [*map(lambda x: x.id, ctx.guild.members)]
        
        users = [*filter(lambda m: not m.id in members or ((ctx.guild.get_member(m.id).top_role < ctx.author.top_role and m.id != ctx.guild.owner_id) or ctx.guild.owner_id == ctx.author.id ), users)]

        reason = f"By {ctx.author.id}: " + reason

        
        if not users:
            return await ctx.reply("Did not find any user that you can ban.")
    

        th = "this" if len(users) == 1 else "these"
        s = "" if len(users) == 1 else "s"

        
        confirm = await ctx.confirm(
            f"Are you sure that you want to ban {th} {len(users)} user{s}?",
            owner=ctx.author.id
        )

        if confirm is True:
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
                failed_to_ban = f"\n{crossmark} | Failed to ban {', '.join(get_names(failed)[:5:])} {and_more(failed)}" if failed else ""
                banned = f"{checkmark} | Banned {', '.join(get_names(success)[:5:])} {and_more(success)}" if success else ""

                embed = SimpleEmbed(
                    self.client,
                    description=f"{banned}{failed_to_ban}"
                )
                embed.set_footer(
                    text=f"Invoked by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar
                )

                await ctx.send(
                    embed=embed,   
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
        ctx: "XynusContext",
        users: commands.Greedy[User],
        *,
        reason: Optional[str] = "No reason provided"
    ):


        bans = [banned.user.id async for banned in ctx.guild.bans()]
        users = [*filter(lambda m: m.id in bans, users)]

        reason = f"[{reason}] - {ctx.author}"



        
        if not users:
            return await ctx.reply("Did not find any user that you can unban.")
    

        th = "this" if len(users) == 1 else "these"
        s = "" if len(users) == 1 else "s"

        
        confirm = await ctx.confirm(
            f"Are you sure that you want to unban {th} {len(users)} user{s}?",
            owner=ctx.author.id
        )

        if confirm is True:
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
                failed_to_unban = f"\n{crossmark} | Failed to unban {', '.join(get_names(failed)[:5:])} {and_more(failed)}" if failed else ""
                unbanned = f"{checkmark} | Unbanned {', '.join(get_names(success)[:5:])} {and_more(success)}" if success else ""

                embed = SimpleEmbed(
                    self.client,
                    description=f"{unbanned}{failed_to_unban}"
                )
                embed.set_footer(
                    text=f"Invoked by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar
                )

                await ctx.send(
                    embed=embed,   
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
        ctx: "XynusContext",
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
        ctx: "XynusContext",
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
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.describe(
        message_id = "The ID of the message you want to delete before it."
    )
    async def purge_until(
        self,
        ctx: "XynusContext",
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
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.describe(
        amount = "Enter a number between 2-1000 to bulk delete messages."
    )
    async def purge_bots(
        self,
        ctx: "XynusContext",
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
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.describe(
        prefix = "The prefix of the commands you want to delete."
    )
    async def purge_commands(
        self,
        ctx: "XynusContext",
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
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.describe(
        user = "Please enter the user.",
        amount = "Enter a number between 2-1000 to bulk delete messages."
    )
    async def purge_user(
        self,
        ctx: "XynusContext",
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
    @commands.has_permissions(
        manage_messages = True
    )
    @app_commands.describe(
        amount = "Enter a number between 2-1000 to bulk delete messages.",
        only_bots = "if enabled, will only delete the messages of bots."
    )
    async def purge_embeds(
        self,
        ctx: "XynusContext",
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
            ctx: "XynusContext"
    ):
        

        total_messages = len(messages)

        s = "" if total_messages == 1 else "s"



        if not await ctx.confirm(
            f"Are you sure that you want to delete {total_messages} message{s}?",
            owner=ctx.author.id
        ):
            return

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