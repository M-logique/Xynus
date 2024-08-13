from ast import parse
from time import time

import discord
from discord.ext import commands

from bot.core import Client, _settings
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import Cog
from bot.templates.embeds import SimpleEmbed
from bot.templates.views import Pagination, PersistentViews, ViewWithDeleteButton
from bot.utils.config import Emojis
from bot.utils.functions import chunker, insert_returns

_emojis = Emojis()
checkmark = _emojis.get("checkmark")


class Owner(Cog):

    def __init__(self, client: Client) -> None:
        
        self.emoji = _emojis.get("crown")

        super().__init__(client)
    



    @commands.command(
        name="eval",
        description="eval some codes.",
        aliases=["e"]
    )
    @commands.is_owner()
    async def eval(
        self,
        ctx: commands.Context,
        *,
        code: str,
    ):
        

        fn_name = "_eval_expr"
        cmd = code.strip("` ")

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = parse(body)
        body = parsed.body[0].body

        insert_returns(body)
        env = {
            'client': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__
        }
        
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = str((await eval(f"{fn_name}()", env)))

        if result == "None":
            return await ctx.message.add_reaction(checkmark)
        

        embed = SimpleEmbed(
            client=self.client,
            description=result[:2000:]
        )

        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar
        )


        if len(result) > 2000:

            async def get_page(
                    index: int
            ):
                chunks = chunker(result, 2000)


                embed.description = chunks[index]


                kwrgs = {
                    "embed": embed
                }

                return kwrgs, len(chunks)

            pagination_view = Pagination(
                get_page=get_page,
                ctx=ctx
            )

            pagination_view.add_item(DeleteButton())

            return await pagination_view.navegate()
        view = ViewWithDeleteButton(ctx.author)
        view.message = await ctx.reply(
            embed=embed,
            silent=True,
            view=view
        )

    @commands.Cog.listener(
        name="on_guild_join"
    )
    async def new_guild_alert(
        self,
        guild: discord.Guild
    ):
        embed = SimpleEmbed(
            client=self.client,
        )

        embed.colour = discord.Color.green()
        members = guild.members
        bots = [*filter(lambda member: member.bot, members)]

        embed.add_field(
            name="👑 Owner",
            value=f"♿️ **Username**: `{guild.owner.name}`\n💠 **ID**: `{guild.owner.id}`\n🔸 **Display**: `{guild.owner.display_name}`",
            inline=False
        )

        if guild.premium_subscription_count != 0:
            
            embed.add_field(
                name=f"💎 Boosts",
                value=f"🤑 **Boosts**: {guild.premium_subscription_count}\n📊 **Level**: `{guild.premium_tier}`\n🤨 **Boosters**: `{len(guild.premium_subscribers)}`",
                inline=False
            )


        embed.add_field(
            name="🥱 Members",
            value=f"🔢 **Total**: `{guild.member_count}`\n🤖 **Bots**: `{len(bots)}`\n🦛 **Humans**: `{len(members) - len(bots)}`"
        )

        embed.set_author(
            name=f"{self.client.user.name} has been invited to {guild.name} #{len(self.client.guilds)}",
            icon_url=self.client.user.avatar
        )

        embed.set_thumbnail(
            url=guild.icon.url
        )

        if guild.banner:
            embed.set_image(
                url=guild.banner.url
            )
        
        if guild.me.guild_permissions.view_audit_log:


            async for entry in guild.audit_logs(
                limit=10,
                action=discord.AuditLogAction.bot_add
            ):
                
                if entry.target and entry.target.id == guild.me.id:
                    embed.set_footer(
                        text=f"Invited by {entry.user} | {entry.user.id}",
                        icon_url=entry.user.avatar
                    )

                    break
        
        channel = await self.client.fetch_channel(_settings.DEV_LOGS_CHANNEL)

        now = int(time())

        await channel.send(
            embed=embed,
            content=(
                f"🔰 **Name**: `{guild.name}`\n"
                f"💠 **ID**: `{guild.id}`\n"
                f"👑 **Owner**: `{guild.owner}`\n"
                f"⌚️ **Timestamp**: <t:{now}:F>"
            ),
            view=PersistentViews.GuildJoinedView(
                self.client
            )
        )
            
        


async def setup(c):

    await c.add_cog(Owner(c))