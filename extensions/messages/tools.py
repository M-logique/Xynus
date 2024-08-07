from time import time
from typing import Optional

from aiohttp import ClientSession
from discord import Interaction, Role, app_commands, utils
from discord.errors import Forbidden, HTTPException
from discord.ext import commands

from bot.core import _settings, guilds
from bot.core.client import Client
from bot.templates.autocomplete import help_autocomplete
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import Cog
from bot.templates.embeds import CommandInfoEmbed, CommandsEmbed, SimpleEmbed
from bot.templates.views import DynamicHelpView, EmojisView, Pagination
from bot.templates.wrappers import check_views, check_views_interaction
from bot.utils.config import Emojis
from bot.utils.functions import (chunker, extract_emoji_info_from_text,
                                 filter_prefix, get_all_commands,
                                 remove_duplicates_preserve_order,
                                 suggest_similar_strings)
from bot import __version__ as version, __name__ as name

_emojis = Emojis()

class Tools(Cog):

    def __init__(self, client: Client) -> None:
        self.emoji = _emojis.get("tools")
        super().__init__(client)
    
    @commands.hybrid_command(
        name="steal",
        description="Steals specified emojis and adds them to the server",
        with_app_command=True,
        aliases=["addemojis"],
        usage=""
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
        
        check_mark = _emojis.get("checkmark")
        cross_mark = _emojis.get("crossmark")
        exclamation = _emojis.get("exclamation")

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
        
        return await ctx.reply(f"{_emojis.get('exclamation')} Didn't find any emoji!")


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

        prefix = await self.client.get_prefix(ctx)
        prefix = filter_prefix(prefix)[0]

        all_commands = get_all_commands(commands=self.list.commands)
        
        embed = CommandsEmbed(
            commands=all_commands,
            title=self.list.description,
            total_commands=len(all_commands),
            prefix=prefix
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

            return await ctx.reply(f"{_emojis('exclamation')} Didn't find any banned member in this server")

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

            return await ctx.reply(f"{_emojis.get('exclamation')} Didn't find any muted member in this server")

        

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

    @commands.command(
        name="help",
        description="Displays the help message",
        aliases=["h"]
    )
    @app_commands.describe(
        cmd = "The command to get help for. If not specified, shows general help information."
    )
    @commands.cooldown(1, 5, commands.BucketType.member)
    @check_views
    async def help_cmd(
        self,
        ctx: commands.Context,
        *,
        cmd: Optional[str] = None
    ):
        

        prefix = await self.client.get_prefix(ctx)
        prefix = filter_prefix(prefix)


        cogs = [self.client.cogs[i] for i in self.client.cogs]


        cogs = [*filter(lambda cog: cog.get_commands() and cog.get_commands() != [], cogs)]

        cog_commands = [get_all_commands(cog=cog) for cog in cogs]
        commands = []
        commands_with_names = {}

        full_name = lambda command: "{}{}{}".format(
            f"{command.root_parent} " if command.root_parent else "",
            f"{command.parent} " if command.parent and command.parent != command.root_parent else "",
            command.name,
        )

        for command in cog_commands: 
            commands+=[*command]
            for command in [*command]:
                commands_with_names[full_name(command)] = command
        
        if cmd:
            similar_strings = suggest_similar_strings(
                target=cmd,
                string_list=[*commands_with_names],
                cutoff=0.6,
                n=5
            )

            if not similar_strings or similar_strings == []:
                return await ctx.reply("No matching command were found.")

            async def get_page(
                    index: int
            ):
                name = similar_strings[index]
                command = commands_with_names[name]
                
                embed = CommandInfoEmbed(
                    self.client,
                    command=command,
                    full_name=name,
                    prefix=prefix
                )

                kwrgs = {
                    "embed": embed
                }

                embed.set_footer(
                    text="Invoked by {}".format(
                        ctx.author.display_name
                    ),
                    icon_url=ctx.author.avatar
                )

                return kwrgs, len(similar_strings)
            

            pagination_view = Pagination(
                get_page=get_page,
                ctx=ctx
            )

            self.client.set_user_view(
                user_id=ctx.author.id,
                view=pagination_view
            )

            pagination_view.add_item(DeleteButton())

            return await pagination_view.navegate()



        dynamic_help_view = DynamicHelpView(
            client=self.client,
            ctx=ctx,
            prefix=prefix,
            bot_commands=commands,
            cogs=self.client.cogs,
        )

        dynamic_help_view.add_item(DeleteButton())

        self.client.set_user_view(
            user_id=ctx.author.id,
            view=dynamic_help_view
        )

        await dynamic_help_view.navegate()

    @app_commands.command(
        name="help",
        description="Displays the help message"
    )
    @app_commands.rename(
        cmd = "command"
    )
    @app_commands.autocomplete(
        cmd = help_autocomplete
    )
    @app_commands.describe(
        cmd = "The command to get help for. If not specified, shows general help information.",
        ephemeral = "Hide the bot's response from other users. (default: False)",
    )
    @app_commands.guilds(*guilds)
    @check_views_interaction
    async def help_slash(
        self,
        inter: Interaction,
        cmd: Optional[str] = None,
        ephemeral: Optional[bool] = False
    ):
        
        prefix = filter_prefix(_settings.PREFIX)

        if cmd:
            bot_commands = {}
            full_name = lambda command: "{}{}{}".format(
                f"{command.root_parent} " if command.root_parent else "",
                f"{command.parent} " if command.parent and command.parent != command.root_parent else "",
                command.name,
            )

            for cog_name in inter.client.cogs:
                cog = inter.client.cogs[cog_name]

                for command in get_all_commands(cog):
                    bot_commands[full_name(command)] = command
            
            command = bot_commands.get(cmd)

            embed = CommandInfoEmbed(
                client=self.client,
                command=command,
                prefix=prefix,
                full_name=cmd
            )

            embed.set_author(
                name=f"{name} - V{version}"
            )


            embed.set_footer(
                text=f"Invoked by {inter.user.display_name}",
                icon_url=inter.user.display_avatar
            )

            return await inter.response.send_message(
                embed=embed,
                ephemeral=ephemeral
            )


        cogs = [self.client.cogs[i] for i in self.client.cogs]
        cogs = [*filter(lambda cog: cog.get_commands() and cog.get_commands() != [], cogs)]

        
        cog_commands = [get_all_commands(cog=cog) for cog in cogs]
        commands = []
        for command in cog_commands: commands+=[*command]



        prefix = filter_prefix(_settings.PREFIX)


        dynamic_help_view = DynamicHelpView(
            client=self.client,
            interaction=inter,
            prefix=prefix,
            bot_commands=commands,
            cogs=self.client.cogs,
        )

        dynamic_help_view.add_item(DeleteButton())

        self.client.set_user_view(
            user_id=inter.user.id,
            view=dynamic_help_view
        )

        await dynamic_help_view.navegate(
            ephemeral=ephemeral
        )


        


async def setup(c): await c.add_cog(Tools(c))