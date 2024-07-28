from time import time
from typing import Optional

from aiohttp import ClientSession
from discord import Role, app_commands, utils
from discord.errors import Forbidden, HTTPException
from discord.ext import commands

from bot.core import guilds
from bot.core.client import Client
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import Cog
from bot.templates.embeds import CommandsEmbed, SimpleEmbed
from bot.templates.views import DynamicHelpView, EmojisView, Pagination
from bot.templates.wrappers import check_views
from bot.utils.config import Emojis
from bot.utils.functions import (chunker, extract_emoji_info_from_text,
                                 remove_duplicates_preserve_order)

_emojis = Emojis()

class Tools(Cog):

    def __init__(self, client: Client) -> None:
        self.emoji = _emojis.global_emojis["tools"]
        super().__init__(client)
    
    @commands.hybrid_command(
        name="steal",
        description="Steals specified emojis and adds them to the server",
        with_app_command=True,
        aliases=["addemojis"]
    )
    @app_commands.guilds(*guilds)
    @app_commands.describe(
        emojis = "List of emojis to be added to the server",
        force_add = "Adds emojis without displaying the pagination (default: False)",
        remove_duplicates = "Removes any duplicate emojis before adding (default: True)"
    )
    @commands.has_permissions(
        manage_emojis_and_stickers = True
    )
    @check_views
    async def steal(
        self,
        ctx: commands.Context,
        *,
        emojis: Optional[str] = None,
        force_add: Optional[bool] = False,
        remove_duplicates: Optional[bool] = True

    ): 
        extracted_emojis = []

        if ctx.message.reference and ctx.message.reference.message_id:
            refrenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            extracted_emojis+=extract_emoji_info_from_text(refrenced_message.content)


        if emojis and extract_emoji_info_from_text(emojis) != []:
            extracted_emojis+=extract_emoji_info_from_text(emojis)

        if remove_duplicates:
            extracted_emojis = remove_duplicates_preserve_order(extracted_emojis)

        async def get_page(index: int):

            extracted_emoji = extracted_emojis[index]

            embed = SimpleEmbed(
                client=self.client,
                title= "Emoji: {} | {}".format(
                    extracted_emoji["name"],
                    extracted_emoji["id"]
                )
            )
            embed.set_footer(
                text="Invoked by {}.".format(
                    ctx.author.display_name
                ),
                icon_url=ctx.author.display_avatar
            )

            url = "https://cdn.discordapp.com/emojis/{}.png".format(
                extracted_emoji.get("id")
            )

            embed.set_image(url=url)

            kwrgs = {
                "embed": embed
            }

            return kwrgs, len(extracted_emojis)
        
        check_mark = _emojis.global_emojis["checkmark"]
        cross_mark = _emojis.global_emojis["crossmark"]
        exclamation = _emojis.global_emojis["exclamation"]

        if extracted_emojis != []:
            if force_add:
                await ctx.send(
                    f"{exclamation} | Started adding {len(extracted_emojis)} emojis"
                )
                for emoji in extracted_emojis:
                    success = 0
                    url = "https://cdn.discordapp.com/emojis/{}.png".format(emoji.get("id"))
                    async with ClientSession() as client:
                        async with client.get(url) as resp:
                            
                            if not resp.status == 200:
                                return await ctx.send(
                                    content="{} | Failed to steal emoji `{}`: Invalid data.".format(
                                        cross_mark,
                                        emoji.get("name")
                                    )
                                )
                            
                            data = await resp.read()
                            

                            try:
                                created_emoji = await ctx.guild.create_custom_emoji(
                                    name=emoji.get("name"),
                                    image=data
                                )
                            
                                emoji = f"<:{created_emoji.name}:{created_emoji.id}>"

                                if created_emoji.animated:
                                    emoji = f"<a:{created_emoji.name}:{created_emoji.id}>"

                                success+=1

                                await ctx.send(
                                    content="{} | Successfully stole emoji: {}.".format(
                                        check_mark,
                                        emoji
                                    )
                                )


                            except Forbidden:

                                await ctx.send(
                                    content="{} | Failed to steal emoji `{}`: 403 error occured.".format(
                                        cross_mark,
                                        emoji.get("name")
                                    )
                                )

                            except HTTPException as e:
                                if e.code == 30008:

                                    await ctx.send(
                                        content="{} | Failed to steal emoji `{}`: The server has reached the maximum number of custom emojis.".format(
                                            cross_mark,
                                            emoji.get("name")
                                        )
                                    )
                                
                                else:
                                    await ctx.send(
                                        content="{} | Failed to steal emoji `{}`: {}.".format(
                                            cross_mark,
                                            emoji.get("name"),
                                            e.text
                                        )
                                    )

                else:
                    return await ctx.send(
                        content=f"{exclamation} The job is done.\n{check_mark} successfull: `{success}`\n{cross_mark} unsuccessfull: `{len(extracted_emojis)-success}`"
                    )


            emojis_view = EmojisView(get_page, ctx=ctx, emojis_dict=extracted_emojis)
            emojis_view.add_item(DeleteButton())

            self.client.set_user_view(
                user_id=ctx.author.id,
                view=emojis_view
            )

            return await emojis_view.navegate()
        
        return await ctx.reply(f"{_emojis.global_emojis['exclamation']} Didn't find any emoji!")


    @commands.hybrid_group(
        name="list",
        description="Commands to retrieve and display lists of information",
        with_app_command=True
    )
    @app_commands.guilds(*guilds)
    async def list(
        self,
        ctx: commands.Context
    ):

        
        
        embed = CommandsEmbed(
            commands=self.list.commands,
            title=self.list.description
        )

        embed.set_footer(
            text="Invoked by {}".format(
                ctx.author.display_name
            ),
            icon_url=ctx.author.display_avatar
        )

        return await ctx.reply(
            embed=embed
        )


    @list.command(
        name="bans",
        description="Displays a list of banned members in the server",
        with_app_command=True
    )
    @app_commands.guilds(*guilds)
    @commands.has_permissions(
        ban_members = True,
    )
    @app_commands.describe(
        ephemeral = "Hide the bot's response from other users. (default: False)",
        limit = "Number of bans to retrieve. (default: All)"
    )
    @check_views
    async def list_bans(
        self,
        ctx: commands.Context,
        ephemeral: Optional[bool] = False,
        limit: Optional[int] = None
    ):
        
        bans = [entry async for entry in ctx.guild.bans(limit=limit)]


        if bans == []:

            return await ctx.reply(f"{_emojis.global_emojis['exclamation']} Didn't find any banned member in this server")

        bans = [
            "`[{}]`: `{}` - `{}`{}".format(
                bans.index(entry) + 1,
                entry.user.name,
                entry.user.id,
                f"*reason:* {entry.reason}" if entry.reason else ""
            )

            for entry in bans
        ]
        

        async def get_page(
                index: int
        ):
            chunks = chunker(bans, 10)

            embed = SimpleEmbed(
                client=self.client,
                description="\n".join(chunks[index]),
                title="Banned members: {}".format(
                    len(bans)
                )
            )

            embed.set_footer(
                text="Invoked by {}.".format(
                    ctx.author.display_name
                ),
                icon_url=ctx.author.display_avatar
            )

            kwrgs = {
                "embed": embed
            }

            return kwrgs, len(chunks)

        pagination_view = Pagination(
            ctx=ctx,
            get_page=get_page
        )

        pagination_view.add_item(DeleteButton())


        self.client.set_user_view(
            user_id=ctx.author.id,
            view=pagination_view
        )


        await pagination_view.navegate(ephemeral=ephemeral)
    
    @list.command(
        name="mutes",
        description="Displays a list of muted members in the server",
        with_app_command=True
    )
    @app_commands.guilds(*guilds)
    @commands.has_permissions(
        ban_members = True,
    )
    @app_commands.describe(
        ephemeral = "Hide the bot's response from other users. (default: False)"
    )
    @check_views
    async def list_mutes(
        self,
        ctx: commands.Context,
        ephemeral: Optional[bool] = False
    ):
        
        muted = [*filter(lambda x: x.timed_out_until is not None and x.timed_out_until.timestamp() > time(), [*ctx.guild.members])]
        muted.sort(key=lambda x: x.timed_out_until.timestamp(), reverse=True)

        muted = [
            "`[{}]`: `{}` - `{}` *expires <t:{}:R>*".format(
                muted.index(entry) + 1,
                entry.name,
                entry.id,
                int(entry.timed_out_until.timestamp())
            )

            for entry in muted
        ]

        if muted == []:

            return await ctx.reply(f"{_emojis.global_emojis['exclamation']} Didn't find any muted member in this server")

        

        async def get_page(
                index: int
        ):
            chunks = chunker(muted, 10)

            embed = SimpleEmbed(
                client=self.client,
                description="\n".join(chunks[index]),
                title="Muted members: {}".format(
                    len(muted)
                )
            )

            embed.set_footer(
                text="Invoked by {}.".format(
                    ctx.author.display_name
                ),
                icon_url=ctx.author.display_avatar
            )

            kwrgs = {
                "embed": embed
            }

            return kwrgs, len(chunks)

        pagination_view = Pagination(
            ctx=ctx,
            get_page=get_page
        )

        pagination_view.add_item(DeleteButton())


        self.client.set_user_view(
            user_id=ctx.author.id,
            view=pagination_view
        )


        await pagination_view.navegate(ephemeral=ephemeral)
    
    @list.command(
        name="members",
        description="Displays a list of members in the server",
        with_app_command=True
    )
    @app_commands.guilds(*guilds)
    @commands.has_permissions(
        ban_members = True,
    )
    @app_commands.rename(
        with_role="with",
        filter_members="filter"
    )
    @app_commands.describe(
        with_role = "Select a role to show only members with  that role (default: All)",
        filter_members = "Select a filter to show only members in that filter (default: All)",
        ephemeral = "Hide the bot's response from other users. (default: False)",

    )
    @app_commands.choices(
        filter_members = [
            app_commands.Choice(
                name="All",
                value="all"
            ),
            app_commands.Choice(
                name="Humans",
                value="humans"
            ),
            app_commands.Choice(
                name="Bots",
                value="bots"
            )
        ]
    )
    @check_views
    async def list_members(
        self,
        ctx: commands.Context,
        with_role: Optional[Role] = None,
        filter_members: app_commands.Choice[str] = "all",
        ephemeral: Optional[bool] = False,
    ):
        
        filtering_cases = {
            "all": lambda x: True,
            "humans": lambda x: not x.bot,
            "bots": lambda x: x.bot
        }

        members = [*filter(filtering_cases.get(filter_members), [*ctx.guild.members])]

        members.sort(key= lambda x: x.joined_at.timestamp())

        #TODO: sort them by joining day

        if with_role:
            members = [*filter(lambda x: utils.get(x.roles, id=with_role.id) is not None, members)]


        members = [
            "`[{}]`: `{}` - `{}` *joined <t:{}:R>*".format(
                members.index(entry) + 1,
                entry.name,
                entry.id,
                int(entry.joined_at.timestamp())
            )

            for entry in members
        ]


        

        async def get_page(
                index: int
        ):
            chunks = chunker(members, 10)

            embed = SimpleEmbed(
                client=self.client,
                description="\n".join(chunks[index]),
                title="{}'s members: {}".format(
                    ctx.guild.name,
                    len(members)
                )
            )

            embed.set_footer(
                text="Invoked by {}.".format(
                    ctx.author.display_name
                ),
                icon_url=ctx.author.display_avatar
            )

            kwrgs = {
                "embed": embed
            }

            return kwrgs, len(chunks)

        pagination_view = Pagination(
            ctx=ctx,
            get_page=get_page
        )

        pagination_view.add_item(DeleteButton())


        self.client.set_user_view(
            user_id=ctx.author.id,
            view=pagination_view
        )


        await pagination_view.navegate(ephemeral=ephemeral)

    @commands.hybrid_command(
        name="help",
        description="Display's the help message",
        aliases=["h"]
    )
    @app_commands.guilds(*guilds)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @check_views
    async def help(
        self,
        ctx: commands.Context,
    ):

        cogs = [self.client.cogs[i] for i in self.client.cogs]

        cog_commands = [cog.get_commands() for cog in cogs]

        commands = []

        for command in cog_commands: commands+=[*command]


        user_accessible_commands = []

        for command in commands:

            if await command.can_run(ctx):
                user_accessible_commands.append(command)


        prefix = await self.client.get_prefix(ctx) if isinstance(await self.client.get_prefix(ctx), str) else list(set(i.strip() for i in await self.client.get_prefix(ctx)))


        dynamic_help_view = DynamicHelpView(
            client=self.client,
            ctx=ctx,
            prefix=prefix,
            bot_commands=commands,
            cogs=self.client.cogs,
            user_accessible_commands=user_accessible_commands
        )

        dynamic_help_view.add_item(DeleteButton())

        self.client.set_user_view(
            user_id=ctx.author.id,
            view=dynamic_help_view
        )

        await dynamic_help_view.navegate()


async def setup(c): await c.add_cog(Tools(c))