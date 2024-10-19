from hashlib import md5
from time import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from aiohttp import ClientSession
from discord import (AllowedMentions, Embed, Interaction, Member, Role,
                     app_commands, utils)
from discord.errors import Forbidden, HTTPException
from discord.ext import commands

from bot.templates.autocomplete import help_autocomplete
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import XynusCog
from bot.templates.embeds import (CommandInfoEmbed, CommandsEmbed,
                                  MappingInfoEmbed, SimpleEmbed)
from bot.templates.flags import EmbedFlags
from bot.templates.modals import WhisperModal
from bot.templates.views import (DuplicatedMappingView, DynamicHelpView,
                                 EmbedEditor, EmojisView, MappingsImportView,
                                 MappingView, Pagination, WhisperModalView,
                                 WhisperView)
from bot.templates.wrappers import check_views, check_views_interaction
from bot.utils.config import Emojis
from bot.utils.functions import (chunker, decrypt, encrypt,
                                 extract_emoji_info_from_text, filter_prefix,
                                 find_command_name, generate_usage,
                                 get_all_commands,
                                 remove_duplicates_preserve_order,
                                 suggest_similar_strings, tuple_remove_item)

if TYPE_CHECKING:
    from bot.core.client import Xynus
    from bot.templates.context import XynusContext

_emojis = Emojis()
checkmark = _emojis.get("checkmark")
crossmark = _emojis.get("crossmark")
exclamation = _emojis.get("exclamation")


class Tools(XynusCog, emoji=_emojis.get("tools")):

    def __init__(self, client: "Xynus") -> None:

        self.embed.usage = generate_usage(self.embed, EmbedFlags)

        super().__init__(client)
    
    @commands.hybrid_command(
        name="steal",
        description="Steals specified emojis and adds them to the server.",
        with_app_command=True,
        aliases=["addemojis"],
        usage=""
    )
    @app_commands.describe(
        emojis = "List of emojis to be added to the server",
        force_add = "Adds emojis without displaying the pagination (default: False)",
        remove_duplicates = "Removes any duplicate emojis before adding (default: True)"
    )
    @commands.has_permissions(
        manage_emojis_and_stickers = True
    )
    @commands.cooldown(1, 10, commands.BucketType.member)
    @check_views
    async def steal(
        self,
        ctx: "XynusContext",
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
                                        crossmark,
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
                                        checkmark,
                                        emoji
                                    )
                                )


                            except Forbidden:

                                await ctx.send(
                                    content="{} | Failed to steal emoji `{}`: 403 error occured.".format(
                                        crossmark,
                                        emoji.get("name")
                                    )
                                )

                            except HTTPException as e:
                                if e.code == 30008:

                                    await ctx.send(
                                        content="{} | Failed to steal emoji `{}`: The server has reached the maximum number of custom emojis.".format(
                                            crossmark,
                                            emoji.get("name")
                                        )
                                    )
                                
                                else:
                                    await ctx.send(
                                        content="{} | Failed to steal emoji `{}`: {}.".format(
                                            crossmark,
                                            emoji.get("name"),
                                            e.text
                                        )
                                    )

                else:
                    return await ctx.send(
                        content=f"{exclamation} The job is done.\n{checkmark} successfull: `{success}`\n{crossmark} unsuccessfull: `{len(extracted_emojis)-success}`"
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
        description="Commands to retrieve and display lists of information.",
        with_app_command=True
    )
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def list(
        self,
        ctx: "XynusContext"
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
            embed=embed,
            delete_button=True
        )


    @list.command(
        name="bans",
        description="Displays a list of banned members in the server.",
        with_app_command=True
    )
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
        ctx: "XynusContext",
        ephemeral: Optional[bool] = False,
        limit: Optional[int] = None
    ):
        
        bans = [entry async for entry in ctx.guild.bans(limit=limit)]


        if bans == []:

            return await ctx.reply(f"{_emojis.get('exclamation')} Didn't find any banned member in this server")

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
        description="Displays a list of muted members in the server.",
        with_app_command=True
    )
    @commands.has_permissions(
        ban_members = True,
    )
    @app_commands.describe(
        ephemeral = "Hide the bot's response from other users. (default: False)"
    )
    @check_views
    async def list_mutes(
        self,
        ctx: "XynusContext",
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
        description="Displays a list of members in the server.",
        with_app_command=True
    )
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
        ctx: "XynusContext",
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
        description="Displays the help message.",
        aliases=["h"]
    )
    @app_commands.describe(
        cmd = "The command to get help for. If not specified, shows general help information."
    )
    @commands.cooldown(1, 5, commands.BucketType.member)
    @check_views
    async def help_cmd(
        self,
        ctx: "XynusContext",
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


        for command in cog_commands: 
            commands+=[*command]
            for command in [*command]:
                commands_with_names[command.qualified_name] = command
        
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
        description="Displays the help message."
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
    @check_views_interaction
    async def help_slash(
        self,
        inter: Interaction,
        cmd: Optional[str] = None,
        ephemeral: Optional[bool] = False
    ):
        
        prefix = ["/"]

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


    @commands.hybrid_command(
        name="whisper",
        description="Whisper a message in a public channel."
    )
    @app_commands.guild_only()
    @app_commands.describe(
        member = "Select a user to whisper",
        text = "Enter the text that you want to whisper"
    )
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def whisper(
        self,
        ctx: "XynusContext",
        member: Member,
        *,
        text: Optional[str] = None
    ):
        
        if ctx.message:
            try: await ctx.message.delete()
            except: ...


        if ctx.author.id == member.id or member.bot:
            await ctx.defer(
                ephemeral=True
            )
            return await ctx.reply(f"{crossmark} | You cannot whisper yourself or a bot user.")
    


        if not text:
            if ctx.interaction:
                return await ctx.interaction.response.send_modal(
                    WhisperModal(
                        target=member,
                    )
                )
            
            await ctx.defer(
                ephemeral=True
            )

            view = WhisperModalView(
                target=member,
                author=ctx.author
            )

            view.add_item(DeleteButton())

            view.message = await ctx.send(
                content=f":eyes: Ok {ctx.author.mention}, now enter your message.",
                view=view
            )

            return
        
        if len(text) > 2000:
            return await ctx.reply(f"{crossmark} | Your text cannot be more than 2000 characters.")
        
        view = WhisperView(
            target=member,
            author=ctx.author,
            text=text
        )

        
        expiry_time = int(time() + 15 * 60)

        if ctx.interaction:
            await ctx.interaction.response.send_message(
                content=f"{checkmark} | Sent in {ctx.channel.mention}",
                ephemeral=True
            )

        view.message = await ctx.channel.send(
            content=f":eyes: {member.mention}, You have a very very very secret message from {ctx.author.mention}!\nYou can only use the button until <t:{expiry_time}:t>.",
            view=view
        )

    @commands.hybrid_group(
            name="mappings",
            aliases=["maps", "mapping"],
            description="Displays commands related to mappings"
    )
    @commands.cooldown(1, 5, commands.BucketType.member)
    @check_views
    async def mappings(self, ctx: "XynusContext"):
        
        cmds = get_all_commands(commands=self.mappings.commands)

        embed = CommandsEmbed(
            commands=cmds,
            title="Mappings",
            total_commands=len(cmds),
            prefix=ctx.clean_prefix
        )

        await ctx.reply(
            embed=embed,
            delete_button=True
        )

    @mappings.command(
        name="set",
        description="Add or edit a custom command mapping",
        aliases=["add", "edit"]
    )
    @app_commands.describe(
        trigger="The trigger phrase that will activate the custom command.",
        command="The command to be executed when the trigger is used."
    )
    async def mappings_set(
        self,
        ctx: "XynusContext",
        trigger: str,
        *,
        command: str
    ):
        trigger = trigger.lower().replace(" ", "")[:20:]
        command_name = find_command_name(command)

        
        if not ctx.client.get_command(command_name):
            return await ctx.reply(
                f"Cannot map `{command_name[:20:]}` as it is not a valid command.",
                allowed_mentions=AllowedMentions.none()
            )
        

        user_cached_maps: Dict[str, Any] = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            keys=[ctx.author.id, trigger],
            create_missing=True
        )


        if len(tuple(user_cached_maps.items())) > 30 and \
                not await ctx.client.is_owner(ctx.user):
            embed = Embed(
                description=f"Sorry but you can't add more than 30 mappings",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )

        sticked_command = ctx.client.get_command(trigger)

        if sticked_command:
            if sticked_command.name == self.mappings.name:
                return await ctx.reply(f"🤔 **for some reasons, you can't add {trigger!r} as your trigger!**")
            
            elif not await ctx.confirm(
                "**You are using one of the bot's commands as a trigger. "
                "This will cause the original command to stop working. "
                "Are you sure you want to use this trigger?**"
            ):
                return

        existant = bool(user_cached_maps.get(trigger))

        query = """
        INSERT INTO mappings(
            user_id,
            trigger,
            command,
            created_at
        )
        VALUES (
            $1,
            $2,
            $3,
            $4
        )
        ON CONFLICT (user_id, trigger)
        DO UPDATE
            SET command = EXCLUDED.command,
                created_at = EXCLUDED.created_at;
        """
        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query, 
                ctx.author.id, 
                encrypt(trigger), 
                encrypt(command),
                int(time())
            )

        ctx.client._cmd_mapping_cache[ctx.author.id][trigger.lower()] = command

        if existant:
            description = f"mapping **{trigger!r}** updated."
        else:
            description = f"Added mapping **{trigger!r}**"
        
        embed = Embed(
            description=description,
            color=ctx.client.color
        )

        await ctx.reply(
            embed=embed,
            delete_button=True
        )

    @mappings.command(
        name="list",
        aliases=["show", "ls", "lst"],
        description="Displays a list of your mappings"
    )
    @app_commands.describe(
        ephemeral="Hide the bot's response from other users. (default: False)"
    )
    async def mappings_list(
        self,
        ctx: "XynusContext",
        ephemeral: Optional[bool] = False
    ):

        cached_items = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id],
            True
        ).get(ctx.author.id, {})


        if not cached_items:
            return await ctx.reply("You don't have any mapping yet!")


        chunks = chunker(tuple(cached_items.items()), 10)

        async def get_page(index: int):

            s = 's' if len(cached_items) > 1 else ''
            embed = Embed(
                title=f"Total {len(cached_items)} mapping{s}",
                color=ctx.client.color,
                description="\n".join(
                    [
                        f"`[{(10*index)+i+1}]`: **`{key}`** - `{value[:20:]}"+f"{'...`' if len(value) > 20 else '`'}"

                        for i, (key, value) in enumerate(chunks[index])
                    ]
                )
            )
            embed.set_footer(
                icon_url=ctx.author.display_avatar,
                text=f"Invoked by {ctx.author.display_name}"
            )

            kwargs = {
                "embed": embed,
            }
            
            return kwargs, len(chunks)

        view = Pagination(get_page, ctx=ctx)
        view.add_item(DeleteButton())

        ctx.client.set_user_view(ctx.author.id, view)
        await view.navegate(ephemeral=ephemeral)


    @mappings.command(
        name="view",
        aliases=["info"],
        description="Displays some information about your mapping"
    )
    @app_commands.describe(
        trigger="The trigger phrase that activates mapping."
    )
    async def mappings_view(
        self, 
        ctx: "XynusContext",
        trigger: str
    ):
        trigger = trigger.lower()

        cached_command = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id, trigger],
            True
        ).get(trigger, None)

        if not cached_command:
            embed = Embed(
                description=f"Didn't find any custom command mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        query = """
        SELECT 
            command, 
            created_at
        FROM 
            mappings
        WHERE 
            trigger = $1
        AND 
            user_id = $2;
        """
        async with ctx.pool.acquire() as conn:
            record = await conn.fetchrow(query, encrypt(trigger), ctx.author.id)

        created_at = record["created_at"]
        command = decrypt(record["command"])

        embed = MappingInfoEmbed(
            ctx,
            trigger,
            command,
            created_at
        )


        view = MappingView(
            ctx.author, 
            command, 
            trigger, 
            created_at, 
            self.mappings,
            "user"
        )

        view.message = await ctx.reply(
            embed=embed,
            view=view
        )


    @mappings.command(
        name="delete",
        aliases=["remove", "del"],
        description="Delete an existing mapping"
    )
    @app_commands.describe(
        trigger="The trigger phrase that activates the mapping."
    )
    async def mappings_delete(
        self,
        ctx: "XynusContext",
        trigger: str
    ):
        trigger = trigger.lower()

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id ,trigger],
            True
        )


        if not data.get(trigger):
            embed = Embed(
                description=f"Didn't find any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        

        query = """
        DELETE FROM mappings
        WHERE user_id = $1
        AND trigger = $2;
        """
        async with ctx.pool.acquire() as conn:
            await conn.fetch(query, ctx.author.id, encrypt(trigger))

        # To prevent the Runtime error here,
        # I made a copy of mappings to iterate
        for key in tuple(ctx.client._cmd_mapping_cache[ctx.author.id].keys()):
            if key == trigger:
                del ctx.client._cmd_mapping_cache[ctx.author.id][trigger]

        await ctx.reply(
            embed=Embed(
                description=f"Removed **{trigger!r}** from your mappings",
                color=ctx.client.color
            ),
            delete_button=True
        )

    @mappings.command(
        name="clear",
        aliases=["removeall"],
        description="Delete all of your mappings"
    )
    async def mappings_clear(
        self,
        ctx: "XynusContext",
    ):

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id],
            True
        ).get(ctx.author.id)


        if not data:
            embed = Embed(
                description=f"You don't have any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        s, th = ('', 'this') if len(data.keys()) == 1 else ('s', 'these')
        
        if not await ctx.confirm(
            "**Are you sure you want to remove "
            f"{th} {len(data.keys())} mapping{s}?**"
        ): 
            return
        

        query = """
        DELETE FROM mappings
        WHERE
            user_id = $1;
        """
        async with ctx.pool.acquire() as conn:
            await conn.fetch(query, ctx.author.id)

        # To prevent the Runtime error here,
        # I made a copy of mappings to iterate
        del ctx.client._cmd_mapping_cache[ctx.author.id]

        await ctx.reply(
            embed=Embed(
                description=f"Removed all of your mappings",
                color=ctx.client.color
            ),
            delete_button=True
        )


    @mappings.command(
        name="copy",
        aliases=["cp"],
        description="to copy one of your mappings"
    )
    @app_commands.describe(
        trigger="The trigger of the mapping that you want to copy",
        new_trigger="The new trigger of the copied mapping"
    )
    async def mappings_copy(
        self,
        ctx: "XynusContext",
        trigger: str,
        new_trigger: str
    ):
        trigger = trigger.lower()
        new_trigger = new_trigger.lower().replace(" ", "")[:20:]

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id ,trigger],
            True
        )


        if not data.get(trigger):
            embed = Embed(
                description=f"Didn't find any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        if data.get(new_trigger):
            return await ctx.reply(
                f"The trigger {new_trigger[:10:]!r} already exists",
                allowed_mentions=AllowedMentions.none()
            )

        query = """
        INSERT INTO mappings (
            trigger,
            command,
            user_id,
            created_at
        )
        SELECT 
            $1, 
            command, 
            user_id, 
            $2
        FROM mappings
        WHERE 
            trigger = $3
        AND 
            user_id = $4;
        """

        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query,
                encrypt(new_trigger),
                int(time()),
                encrypt(trigger),
                ctx.author.id
            )
        
        ctx.client._cmd_mapping_cache[ctx.author.id][new_trigger] = data.get(trigger)

        embed = Embed(
            color=ctx.client.color,
            description=f"Created a copy of {trigger!r} with the trigger **{new_trigger!r}**."
        )
        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar
        )

        await ctx.reply(
            embed=embed,
            delete_button=True
        )

    @mappings.command(
        name="share",
        description="to create a share code of your mapping"
    )
    @app_commands.describe(
        trigger="The trigger of the mapping that you want to share"
    )
    async def mappings_share(
        self,
        ctx: "XynusContext",
        trigger: str
    ):
        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id ,trigger],
            True
        )

        if not data.get(trigger):
            embed = Embed(
                description=f"Didn't find any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        conn = await ctx.pool.acquire()
        encrypted_trigger = encrypt(trigger)

        selection_query = """
        SELECT id, share_code FROM mappings
        WHERE 
            user_id = $1
        AND   
            trigger = $2;
        """


        result = await conn.fetchrow(
            selection_query,
            ctx.author.id,
            encrypted_trigger
        )
        
        mapping_id = result["id"]
        share_code = result["share_code"]
        if not share_code:
            share_code = md5(str(mapping_id).encode()).hexdigest()

            insertion_query = """
            UPDATE mappings
            SET 
                share_code = $1
            WHERE
                user_id = $2
            AND 
                trigger = $3
            """

            await conn.fetch(
                insertion_query,
                share_code,
                ctx.author.id,
                encrypted_trigger
            )

        await ctx.pool.release(conn)

        embed = Embed(
            description=f"**Here is a share code of the mapping {trigger!r}:** `{share_code}`",
            color=ctx.client.color
        )

        embed.add_field(
            name="💡 Tip",
            value=f"Use `mappings import {share_code}` to add this mapping to your mappings"
        )

        view = MappingsImportView(
            share_code
        )

        await ctx.reply(
            embed=embed,
            view=view
        )
        
        

    @mappings.command(
        name="import",
        description="to import a mapping by using its share code"
    )
    @app_commands.describe(
        share_code="The share code that generated using 'mappings share' command"
    )
    async def mappings_import(
        self,
        ctx: "XynusContext",
        share_code: str
    ):
        
        conn = await ctx.pool.acquire()

        selection_query = """
        SELECT * 
        FROM mappings
        WHERE share_code = $1;
        """

        record = await conn.fetchrow(
            selection_query,
            share_code
        )

        if not record:
            await ctx.pool.release(conn)
            return await ctx.reply("Didn't find any mapping")
        
        trigger = decrypt(record["trigger"])
        command = decrypt(record["command"])

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.author.id ,trigger],
            True
        )
        if not await ctx.confirm(
            f"**Are you sure you want to import the mapping {trigger!r}?**"
        ):
            return

        if data.get(trigger):
            view = DuplicatedMappingView(
                share_code=share_code,
                command=command,
                trigger=trigger,
                author=ctx.author,
                import_type="user"
            )

            return await ctx.reply(
                f"Trigger {trigger!r} already exists, so choose an option:",
                view=view,
                allowed_mentions=AllowedMentions.none()
            )

        encrypted_trigger =  encrypt(trigger)


        
        insertion_query = """
        INSERT INTO mappings(
            user_id,
            trigger,
            command,
            created_at
        )
        SELECT 
            $1,
            $2,
            command,
            $3
        
        FROM mappings 
        WHERE 
            share_code = $4; 
        """

        await conn.fetch(
            insertion_query,
            ctx.author.id,
            encrypted_trigger,
            int(time()),
            share_code
        )

        await ctx.pool.release(conn)
        
        decrypted_trigger = decrypt(encrypted_trigger)
        ctx.client._cmd_mapping_cache[ctx.author.id][decrypted_trigger] = command
        
        await ctx.reply(
            f"**Added {decrypted_trigger!r} to your mappings**",
            allowed_mentions=AllowedMentions.none()
        )

    @mappings.group(
        name="guild",
        description="Displays a list of guild mappings",
        aliases=["g", "server", "sv"],
        fallback="list"
    )
    @app_commands.describe(
        ephemeral = "Hide the bot's response from other users. (default: False)",
    )
    async def mappings_group(
        self,
        ctx: "XynusContext",
        ephemeral: Optional[bool] = False
    ):
        cached_items = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id],
            True
        ).get(ctx.guild.id, {})


        if not cached_items:
            return await ctx.reply("There is no mapping here yet!")


        chunks = chunker(tuple(cached_items.items()), 10)

        async def get_page(index: int):

            s = 's' if len(cached_items) > 1 else ''
            embed = Embed(
                title=f"Total {len(cached_items)} mapping{s}",
                color=ctx.client.color,
                description="\n".join(
                    [
                        f"`[{(10*index)+i+1}]`: **`{key}`** - `{value[:20:]}"+f"{'...`' if len(value) > 20 else '`'}"

                        for i, (key, value) in enumerate(chunks[index])
                    ]
                )
            )
            embed.set_footer(
                icon_url=ctx.author.display_avatar,
                text=f"Invoked by {ctx.author.display_name}"
            )

            kwargs = {
                "embed": embed,
            }
            
            return kwargs, len(chunks)

        view = Pagination(get_page, ctx=ctx)
        view.add_item(DeleteButton())

        ctx.client.set_user_view(ctx.author.id, view)
        await view.navegate(ephemeral=ephemeral)

    @mappings_group.command(
        name="set",
        description="Add or edit a custom command mapping",
        aliases=["add", "edit"]
    )
    @app_commands.describe(
        trigger="The trigger phrase that will activate the custom command.",
        command="The command to be executed when the trigger is used."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    @app_commands.guild_only()
    async def mappings_guild_set(
        self,
        ctx: "XynusContext",
        trigger: str,
        *,
        command: str
    ):
        trigger = trigger.lower().replace(" ", "")[:20:]
        command_name = find_command_name(command)

        
        if not ctx.client.get_command(command_name):
            return await ctx.reply(
                f"Cannot map `{command_name[:20:]}` as it is not a valid command.",
                allowed_mentions=AllowedMentions.none()
            )
        

        user_cached_maps: Dict[str, Any] = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            keys=[ctx.guild.id, trigger],
            create_missing=True
        )


        if len(tuple(user_cached_maps.items())) > 30 and \
                not ctx.client.is_owner(ctx.user):
            embed = Embed(
                description=f"Sorry but you can't add more than 30 mappings",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )

        sticked_command = ctx.client.get_command(trigger)

        if sticked_command:
            if sticked_command.name == self.mappings.name:
                return await ctx.reply(f"🤔 **for some reasons, you can't add {trigger!r} as your trigger!**")
            
            elif not await ctx.confirm(
                "**You are using one of the bot's commands as a trigger. "
                "This will cause the original command to stop working. "
                "Are you sure you want to use this trigger?**"
            ):
                return

        existant = bool(user_cached_maps.get(trigger))

        query = """
        INSERT INTO mappings(
            guild_id,
            trigger,
            command,
            created_at
        )
        VALUES (
            $1,
            $2,
            $3,
            $4
        )
        ON CONFLICT (guild_id, trigger)
        DO UPDATE
            SET command = EXCLUDED.command,
                created_at = EXCLUDED.created_at;
        """
        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query, 
                ctx.guild.id, 
                encrypt(trigger), 
                encrypt(command),
                int(time())
            )

        ctx.client._cmd_mapping_cache[ctx.guild.id][trigger.lower()] = command

        if existant:
            description = f"mapping **{trigger!r}** updated."
        else:
            description = f"Added mapping **{trigger!r}**"
        
        embed = Embed(
            description=description,
            color=ctx.client.color
        )

        await ctx.reply(
            embed=embed,
            delete_button=True
        )    

    @mappings_group.command(
        name="view",
        aliases=["info"],
        description="Displays some information about a mapping"
    )
    @app_commands.describe(
        trigger="The trigger phrase that activates mapping."
    )
    async def mappings_guild_view(
        self, 
        ctx: "XynusContext",
        trigger: str
    ):
        trigger = trigger.lower()

        cached_command = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id, trigger],
            True
        ).get(trigger, None)

        if not cached_command:
            embed = Embed(
                description=f"Didn't find any custom command mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        query = """
        SELECT 
            command, 
            created_at
        FROM 
            mappings
        WHERE 
            trigger = $1
        AND 
            guild_id = $2;
        """
        async with ctx.pool.acquire() as conn:
            record = await conn.fetchrow(query, encrypt(trigger), ctx.guild.id)

        created_at = record["created_at"]
        command = decrypt(record["command"])

        embed = MappingInfoEmbed(
            ctx,
            trigger,
            command,
            created_at
        )


        view = MappingView(
            ctx.author, 
            command, 
            trigger, 
            created_at, 
            self.mappings,
            "guild"
        )

        view.message = await ctx.reply(
            embed=embed,
            view=view
        )


    @mappings_group.command(
        name="delete",
        aliases=["remove", "del"],
        description="Delete an existing mapping"
    )
    @app_commands.describe(
        trigger="The trigger phrase that activates the mapping."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    @app_commands.guild_only()
    async def mappings_guild_delete(
        self,
        ctx: "XynusContext",
        trigger: str
    ):
        trigger = trigger.lower()

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id ,trigger],
            True
        )
    

        if not data.get(trigger):
            embed = Embed(
                description=f"Didn't find any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        

        query = """
        DELETE FROM mappings
        WHERE guild_id = $1
        AND trigger = $2;
        """
        async with ctx.pool.acquire() as conn:
            await conn.fetch(query, ctx.guild.id, encrypt(trigger))

        # To prevent the Runtime error here,
        # I made a copy of mappings to iterate
        for key in tuple(ctx.client._cmd_mapping_cache[ctx.guild.id].keys()):
            if key == trigger:
                del ctx.client._cmd_mapping_cache[ctx.guild.id][trigger]

        await ctx.reply(
            embed=Embed(
                description=f"Removed **{trigger!r}** from mappings",
                color=ctx.client.color
            ),
            delete_button=True
        )

    @mappings_group.command(
        name="clear",
        aliases=["removeall"],
        description="Delete all of guild mappings"
    )
    @commands.has_permissions(
        manage_guild=True
    )
    @app_commands.guild_only()
    async def mappings_guild_clear(
        self,
        ctx: "XynusContext",
    ):

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id],
            True
        ).get(ctx.guild.id)


        if not data:
            embed = Embed(
                description=f"There is no mapping here yet!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        s, th = ('', 'this') if len(data.keys()) == 1 else ('s', 'these')
        
        if not await ctx.confirm(
            "**Are you sure you want to remove "
            f"{th} {len(data.keys())} mapping{s}?**"
        ): 
            return
        

        query = """
        DELETE FROM mappings
        WHERE
            guild = $1;
        """
        async with ctx.pool.acquire() as conn:
            await conn.fetch(query, ctx.guild.id)

        # To prevent the Runtime error here,
        # I made a copy of mappings to iterate
        del ctx.client._cmd_mapping_cache[ctx.guild.id]

        await ctx.reply(
            embed=Embed(
                description=f"Removed all mappings",
                color=ctx.client.color
            ),
            delete_button=True
        )


    @mappings_group.command(
        name="copy",
        aliases=["cp"],
        description="to copy one of guild mappings"
    )
    @app_commands.describe(
        trigger="The trigger of the mapping that you want to copy",
        new_trigger="The new trigger of the copied mapping"
    )
    @commands.has_permissions(
        manage_guild=True
    )
    @app_commands.guild_only()
    async def mappings_guild_copy(
        self,
        ctx: "XynusContext",
        trigger: str,
        new_trigger: str
    ):
        trigger = trigger.lower()
        new_trigger = new_trigger.lower().replace(" ", "")[:20:]

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id ,trigger],
            True
        )


        if not data.get(trigger):
            embed = Embed(
                description=f"Didn't find any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        if data.get(new_trigger):
            return await ctx.reply(
                f"The trigger {new_trigger[:10:]!r} already exists",
                allowed_mentions=AllowedMentions.none()
            )

        query = """
        INSERT INTO mappings (
            trigger,
            command,
            guild_id,
            created_at
        )
        SELECT 
            $1, 
            command, 
            guild_id, 
            $2
        FROM mappings
        WHERE 
            trigger = $3
        AND 
            guild_id = $4;
        """

        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query,
                encrypt(new_trigger),
                int(time()),
                encrypt(trigger),
                ctx.guild.id
            )
        
        ctx.client._cmd_mapping_cache[ctx.guild.id][new_trigger] = data.get(trigger)

        embed = Embed(
            color=ctx.client.color,
            description=f"Created a copy of {trigger!r} with the trigger **{new_trigger!r}**."
        )
        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar
        )

        await ctx.reply(
            embed=embed,
            delete_button=True
        )

    @mappings_group.command(
        name="share",
        description="to create a share code of your mapping"
    )
    @app_commands.describe(
        trigger="The trigger of the mapping that you want to share"
    )
    @commands.has_permissions(
        manage_guild=True
    )
    @app_commands.guild_only()
    async def mappings_guild_share(
        self,
        ctx: "XynusContext",
        trigger: str
    ):
        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id ,trigger],
            True
        )

        if not data.get(trigger):
            embed = Embed(
                description=f"Didn't find any mapping!",
                color=ctx.client.color
            )
            return await ctx.reply(
                embed=embed,
                delete_button=True
            )
        
        conn = await ctx.pool.acquire()
        encrypted_trigger = encrypt(trigger)

        selection_query = """
        SELECT id, share_code FROM mappings
        WHERE 
            guild_id = $1
        AND   
            trigger = $2;
        """


        result = await conn.fetchrow(
            selection_query,
            ctx.guild.id,
            encrypted_trigger
        )
        
        mapping_id = result["id"]
        share_code = result["share_code"]
        if not share_code:
            share_code = md5(str(mapping_id).encode()).hexdigest()

            insertion_query = """
            UPDATE mappings
            SET 
                share_code = $1
            WHERE
                guild_id = $2
            AND 
                trigger = $3
            """

            await conn.fetch(
                insertion_query,
                share_code,
                ctx.guild.id,
                encrypted_trigger
            )

        await ctx.pool.release(conn)

        embed = Embed(
            description=f"**Here is a share code of the mapping {trigger!r}:** `{share_code}`",
            color=ctx.client.color
        )

        embed.add_field(
            name="💡 Tip",
            value=f"Use `mappings import {share_code}` to add this mapping to your mappings"
        )

        view = MappingsImportView(
            share_code
        )

        await ctx.reply(
            embed=embed,
            view=view
        )
        
        

    @mappings_group.command(
        name="import",
        description="to import a mapping by using its share code"
    )
    @app_commands.describe(
        share_code="The share code that generated using 'mappings share' command"
    )
    @commands.has_permissions(
        manage_guild=True
    )
    @app_commands.guild_only()
    async def mappings_guild_import(
        self,
        ctx: "XynusContext",
        share_code: str
    ):
        
        conn = await ctx.pool.acquire()

        selection_query = """
        SELECT * 
        FROM mappings
        WHERE share_code = $1;
        """

        record = await conn.fetchrow(
            selection_query,
            share_code
        )

        if not record:
            await ctx.pool.release(conn)
            return await ctx.reply("Didn't find any mapping")
        
        trigger = decrypt(record["trigger"])
        command = decrypt(record["command"])

        data = ctx.db._traverse_dict(
            ctx.client._cmd_mapping_cache,
            [ctx.guild.id ,trigger],
            True
        )
        if not await ctx.confirm(
            f"**Are you sure you want to import the mapping {trigger!r}?**"
        ):
            return

        if data.get(trigger):
            view = DuplicatedMappingView(
                share_code=share_code,
                command=command,
                trigger=trigger,
                author=ctx.author,
                import_type="guild"
            )

            return await ctx.reply(
                f"Trigger {trigger!r} already exists, so choose an option:",
                view=view,
                allowed_mentions=AllowedMentions.none()
            )

        encrypted_trigger =  encrypt(trigger)


        
        insertion_query = """
        INSERT INTO mappings(
            guild_id,
            trigger,
            command,
            created_at
        )
        SELECT 
            $1,
            $2,
            command,
            $3
        
        FROM mappings 
        WHERE 
            share_code = $4; 
        """

        await conn.fetch(
            insertion_query,
            ctx.guild.id,
            encrypted_trigger,
            int(time()),
            share_code
        )

        await ctx.pool.release(conn)
        
        decrypted_trigger = decrypt(encrypted_trigger)
        ctx.client._cmd_mapping_cache[ctx.guild.id][decrypted_trigger] = command
        
        await ctx.reply(
            f"**Added {decrypted_trigger!r} to your mappings**",
            allowed_mentions=AllowedMentions.none()
        )
    
    # TODO: fix maps info for guilds.
    # TODO: add reload command that reloads cache.
    # TODO: ادد دادن یچیزی برای کامند هلپ که اگر زد "کمک مپینگ" کامند مپ شده پیدا کنه بده بهش

    @commands.hybrid_group(
        name="prefixes",
        aliases=["prefix"],
        fallback="list",
        description="Retrives a list of available prefixes"
    )
    async def prefixes( 
        self,
        ctx: "XynusContext"
    ):

        guild_prefixes = (ctx.me.mention, )
        cached_prefixes = ctx.client._prefix_cache.get(ctx.author.id, tuple())
        user_prefixes = (ctx.me.mention, ) + cached_prefixes
        if ctx.guild:
            guild_prefixes+=ctx.client._prefix_cache.get(ctx.guild.id, tuple())
        


        embed = Embed(
            color=ctx.client.color
        )
        
        embed.set_author(
            icon_url=ctx.author.display_avatar,
            name=f"{ctx.author.display_name}"
        )
        
        if len(user_prefixes) > 1:
            embed.add_field(
                name=f"{ctx.author.display_name}'s prefixes",
                value="\n".join(
                    (
                        f"{i+1}. {prefix}"

                        for i, prefix in enumerate(user_prefixes)
                    )
                ),
                inline=False
            )
        
        if len(guild_prefixes) > 1:
            embed.add_field(
                name=f"{ctx.guild.name}'s prefixes",
                value="\n".join(
                    (
                        f"{i+1}. {prefix}"

                        for i, prefix in enumerate(guild_prefixes)
                    )
                ),
                inline=False
            )
        
        if len(guild_prefixes) == 1 and len(user_prefixes) == 1:
            embed.description = "\n".join(
                (
                    f"{i+1}. {prefix}"

                    for i, prefix in enumerate(ctx.client._settings.PREFIX)
                )
            )



        await ctx.reply(embed=embed)
        

    @prefixes.command(
        name="add",
        description="Add a custom prefix for yourself"
    )
    async def prefixes_add(
        self,
        ctx: "XynusContext",
        prefix: str
    ):
        prefix = prefix[:5:].strip().lower()

        cached_prefixes = ctx.client.db._traverse_dict(
            ctx.client._prefix_cache,
            [ctx.author.id],
            True
        ).get(ctx.author.id, tuple())

        if prefix in cached_prefixes:
            return await ctx.reply("This prefix is already in your prefixes.")
        
        conn = await ctx.pool.acquire()

        query = """
        INSERT INTO prefixes(
            user_id,
            prefixes
        )
        VALUES(
            $1,
            ARRAY[$2]::TEXT[]
        )
        ON CONFLICT (user_id)
        DO UPDATE 
        SET prefixes = ARRAY_CAT(
            prefixes.prefixes, 
            EXCLUDED.prefixes
        );
        """
        if not cached_prefixes:
            for default_prefix in ctx.client._settings.PREFIX:
                await conn.fetch(
                    query,
                    ctx.author.id,
                    encrypt(default_prefix)
                )
                ctx.client._prefix_cache[ctx.author.id] = cached_prefixes + (default_prefix, )
                cached_prefixes = ctx.client.db._traverse_dict(
                    ctx.client._prefix_cache,
                    [ctx.author.id],
                    True
                ).get(ctx.author.id, tuple())

        encrypted_prefix = encrypt(prefix)

        await conn.fetch(
            query,
            ctx.author.id,
            encrypted_prefix
        )

        await ctx.pool.release(conn)

        ctx.client._prefix_cache[ctx.author.id] = cached_prefixes + (prefix, )
        await ctx.reply(
            f"Added {prefix} to your prefixes",
            allowed_mentions=AllowedMentions.none()
        )
        
    @prefixes.command(
        name="set",
        descroption="Replaces all custom prefixes set to the specified prefix (Mention still works)"
    )
    async def prefixes_set(
        self,
        ctx: "XynusContext",
        prefix: str
    ):
        prefix = prefix[:5:].strip().lower()

        if not await ctx.confirm(
            "Are you sure you want to set your prefix to"
            f" {prefix}? your previouse prefixes will be deleted"
            " permanently."
        ): return

        query = """
        INSERT INTO prefixes(
            user_id,
            prefixes
        )
        VALUES(
            $1,
            ARRAY[$2]::TEXT[]
        )
        ON CONFLICT (user_id)
        DO UPDATE 
        SET prefixes = EXCLUDED.prefixes
        """

        encrypted_prefix = encrypt(prefix)
        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query,
                ctx.author.id,
                encrypted_prefix
            )

        ctx.client._prefix_cache[ctx.author.id] = (prefix, )
        await ctx.reply(
            f"Now your prefix is {prefix!r}.",
            allowed_mentions=AllowedMentions.none()
        )

    @prefixes.command(
        name="remove",
        aliases=["delete", "del", "rm"]
    )
    async def prefixes_remove(
        self,
        ctx: "XynusContext",
        prefix: str
    ):
        prefix = prefix[:5:].strip().lower()

        cached_prefixes = ctx.client.db._traverse_dict(
            ctx.client._prefix_cache,
            [ctx.author.id],
            True
        ).get(ctx.author.id, tuple())

        if not prefix in cached_prefixes:
            return await ctx.reply(
                f"You don't have any prefix called {prefix!r}.",
                allowed_mentions=AllowedMentions.none()
            )
        
        conn = await ctx.pool.acquire()
        query = """
        UPDATE prefixes 
        SET prefixes = ARRAY_REMOVE(
            prefixes, 
            $1
        )
        WHERE 
            user_id = $2;
        """

        await conn.fetch(
            query,
            encrypt(prefix),
            ctx.author.id
        )

        ctx.client._prefix_cache[ctx.author.id] = tuple_remove_item(
            ctx.client._prefix_cache[ctx.author.id], 
            prefix
        )

        if not ctx.client._prefix_cache.get(ctx.author.id):
            del ctx.client._prefix_cache[ctx.author.id]
            deletion_query = """
            DELETE FROM prefixes 
            WHERE user_id = $1;
            """

            await conn.fetch(
                deletion_query,
                ctx.author.id
            )

            

        await ctx.reply(
            f"Removed {prefix!r} from your prefixes",
            allowed_mentions=AllowedMentions.none()
        )


    @prefixes.command(
        name="clear",
        aliases=["reset"],
        description="Removes all prefixes"
    )
    async def prefixes_reset(
        self,
        ctx: "XynusContext",
    ):
        conn = await ctx.pool.acquire()
        selection_query = """
        SELECT * FROM prefixes 
        WHERE user_id = $1;
        """

        data = await conn.fetchrow(
            selection_query,
            ctx.author.id
        )

        if not data:
            await ctx.reply("You don't have any prefixes")
            return await ctx.pool.release(conn)

        if not await ctx.confirm(
            "Are you sure? this will delete all"
            " of your prefixes"
        ): return await ctx.pool.release(conn)

        
        query = """
        DELETE FROM prefixes
        WHERE 
            user_id = $1;
        """
        await conn.execute(
            query,
            ctx.author.id
        )
        await ctx.pool.release(conn)

        del ctx.client._prefix_cache[ctx.author.id]
        await ctx.reply("Your prefixes has been reset.")


    @prefixes.group(
        name="guild",
        description="Retrives a list of available prefixes",
        aliases=["g", "sv", "server"],
        fallback="list"
    )
    @commands.guild_only()
    async def prefixes_guild(
        self,
        ctx: "XynusContext"
    ):
        return await self.prefixes(ctx)
    

    @prefixes_guild.command(
        name="add",
        description="Add a custom prefix for yourself"
    )
    @commands.has_permissions(
        manage_guild = True
    )
    async def prefixes_guild_add(
        self,
        ctx: "XynusContext",
        prefix: str
    ):
        prefix = prefix[:5:].strip().lower()

        cached_prefixes = ctx.client.db._traverse_dict(
            ctx.client._prefix_cache,
            [ctx.guild.id],
            True
        ).get(ctx.guild.id, tuple())

        if prefix in cached_prefixes:
            return await ctx.reply(
                f"This prefix is already in {ctx.guild.name}'s prefixes.",
                allowed_mentions=AllowedMentions.none()
            )
        
        conn = await ctx.pool.acquire()

        query = """
        INSERT INTO prefixes(
            guild_id,
            prefixes
        )
        VALUES(
            $1,
            ARRAY[$2]::TEXT[]
        )
        ON CONFLICT (guild_id)
        DO UPDATE 
        SET prefixes = ARRAY_CAT(
            prefixes.prefixes, 
            EXCLUDED.prefixes
        );
        """
        if not cached_prefixes:
            for default_prefix in ctx.client._settings.PREFIX:
                await conn.fetch(
                    query,
                    ctx.guild.id,
                    encrypt(default_prefix)
                )
                ctx.client._prefix_cache[ctx.guild.id] = cached_prefixes + (default_prefix, )
                cached_prefixes = ctx.client.db._traverse_dict(
                    ctx.client._prefix_cache,
                    [ctx.guild.id],
                    True
                ).get(ctx.guild.id, tuple())

        encrypted_prefix = encrypt(prefix)

        await conn.fetch(
            query,
            ctx.guild.id,
            encrypted_prefix
        )

        await ctx.pool.release(conn)

        ctx.client._prefix_cache[ctx.guild.id] = cached_prefixes + (prefix, )
        await ctx.reply(
            f"Added {prefix} to server prefixes.",
            allowed_mentions=AllowedMentions.none()
        )
        
    @prefixes_guild.command(
        name="set",
        descroption="Replaces all custom prefixes set to the specified prefix (Mention still works)"
    )
    @commands.has_permissions(
        manage_guild = True
    )
    async def prefixes_guild_set(
        self,
        ctx: "XynusContext",
        prefix: str
    ):
        prefix = prefix[:5:].strip().lower()

        if not await ctx.confirm(
            "Are you sure you want to set server prefix to"
            f" {prefix}? the previouse prefixes will be deleted"
            " permanently."
        ): return

        query = """
        INSERT INTO prefixes(
            guild_id,
            prefixes
        )
        VALUES(
            $1,
            ARRAY[$2]::TEXT[]
        )
        ON CONFLICT (guild_id)
        DO UPDATE 
        SET prefixes = EXCLUDED.prefixes;
        """

        encrypted_prefix = encrypt(prefix)
        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query,
                ctx.guild.id,
                encrypted_prefix
            )

        ctx.client._prefix_cache[ctx.guild.id] = (prefix, )
        await ctx.reply(
            f"Now your prefix is {prefix!r}.",
            allowed_mentions=AllowedMentions.none()
        )

    @prefixes_guild.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        description="Removes a prefix from guild's prefixes"
    )
    @commands.has_permissions(
        manage_guild = True
    )
    async def prefixes_guild_remove(
        self,
        ctx: "XynusContext",
        prefix: str
    ):
        prefix = prefix[:5:].strip().lower()

        cached_prefixes = ctx.client.db._traverse_dict(
            ctx.client._prefix_cache,
            [ctx.guild.id],
            True
        ).get(ctx.guild.id, tuple())

        if not prefix in cached_prefixes:
            return await ctx.reply(
                f"there is not prefix called {prefix!r}.",
                allowed_mentions=AllowedMentions.none()
            )
        query = """
        UPDATE prefixes 
        SET prefixes = ARRAY_REMOVE(
            prefixes,
            $1
        )
        WHERE 
            guild_id = $2;
        """

        async with ctx.pool.acquire() as conn:
            await conn.fetch(
                query,
                encrypt(prefix),
                ctx.guild.id
            )
        
        ctx.client._prefix_cache[ctx.guild.id] = tuple_remove_item(
            ctx.client._prefix_cache[ctx.guild.id], 
            prefix
        )

        await ctx.reply(
            f"Removed {prefix!r} from prefixes.",
            allowed_mentions=AllowedMentions.none()
        )


    @prefixes_guild.command(
        name="clear",
        aliases=["reset"],
        description="Removes all guild prefixes"
    )
    @commands.has_permissions(
        manage_guild = True
    )
    async def prefixes_guild_reset(
        self,
        ctx: "XynusContext",
    ):
        conn = await ctx.pool.acquire()
        selection_query = """
        SELECT * FROM prefixes 
        WHERE guild_id = $1;
        """

        data = await conn.fetchrow(
            selection_query,
            ctx.guild.id
        )

        if not data:
            await ctx.reply("There is no prefixes here")
            return await ctx.pool.release(conn)

        if not await ctx.confirm(
            "Are you sure? this will delete all"
            " prefixes"
        ): return await ctx.pool.release(conn)

        query = """
        DELETE FROM prefixes
        WHERE 
            guild_id = $1;
        """

        await conn.fetch(
            query,
            ctx.guild.id
        )

        await ctx.pool.release(conn)
        del ctx.client._prefix_cache[ctx.guild.id]
        await ctx.reply("Your prefixes has been reset.")



    # Embed builder from HideoutManager
    # https://github.com/DuckBot-Discord/duck-hideout-manager-bot/


    @commands.command(
        description="Sends an embed using flags. An interactive embed maker is also available if you don't pass any flags.",
    )
    async def embed(
        self,
        ctx: "XynusContext",
        *,
        flags: Optional[EmbedFlags],
    ):
        
        if flags is None:
            view = EmbedEditor(ctx.author, self)  # type: ignore

            if ctx.reference and ctx.reference.embeds:
                view.embed = Embed.from_dict(ctx.reference.embeds[0].to_dict())
                await view.update_buttons()
            view.message = await ctx.send(embed=view.current_embed, view=view)
            return


        embed = Embed(title=flags.title, description=flags.description, colour=flags.color)

        if flags.field and len(flags.field) > 25:
            raise commands.BadArgument('You can only have up to 25 fields!')

        for f in flags.field or []:
            embed.add_field(name=f.name, value=f.value, inline=f.inline)

        if flags.thumbnail:
            embed.set_thumbnail(url=flags.thumbnail)

        if flags.image:
            embed.set_image(url=flags.image)

        if flags.author:
            embed.set_author(name=flags.author.name, url=flags.author.url, icon_url=flags.author.icon)

        if flags.footer:
            embed.set_footer(text=flags.footer.text, icon_url=flags.footer.icon or None)

        if not embed:
            raise commands.BadArgument('You must pass at least one of the necessary (marked with `*`) flags!')
        if len(embed) > 6000:
            raise commands.BadArgument('The embed is too big! (too much text!) Max length is 6000 characters.')
        try:
            await ctx.channel.send(embed=embed)
        except HTTPException as e:
            raise commands.BadArgument(f'Failed to send the embed! {type(e).__name__}: {e.text}`')
        except Exception as e:
            raise commands.BadArgument(f'An unexpected error occurred: {type(e).__name__}: {e}') 

async def setup(c): 
    c.remove_command("help")
    await c.add_cog(Tools(c))