from asyncio import sleep
from copy import deepcopy
from re import search as _search
from string import Template
from time import time
from typing import (TYPE_CHECKING, Any, Callable, Dict, Literal, Optional,
                    Self, Sequence, Union)

from aiohttp import ClientSession
from asyncpg import Pool
from discord import (Button, ButtonStyle, ChannelType, Embed, Interaction,
                     Member, Message, NotFound, Object, PermissionOverwrite,
                     User)
from discord.abc import Messageable
from discord.components import SelectOption
from discord.errors import Forbidden, HTTPException
from discord.ext import commands
from discord.ui import Button as Btn
from discord.ui import ChannelSelect
from discord.ui import Select
from discord.ui import Select as _Select
from discord.ui import View as _View
from discord.ui import button, select
from discord.ui.item import Item
from kv.kvpostgres import KVDatabase

from bot import __version__ as version

from ..utils.config import Emojis
from ..utils.functions import chunker as _chunker
from ..utils.functions import decrypt
from ..utils.functions import disable_all_items as _disable_all_items
from ..utils.functions import encrypt
from ..utils.functions import get_all_commands as _get_all_commands
from ..utils.functions import random_string
from .buttons import DeleteButton, EditWithModalButton
from .cooldowns import ticket_edit_cooldown
from .embeds import (CommandsEmbed, DynamicHelpEmbed, ErrorEmbed,
                     MappingInfoEmbed)
from .exceptions import CustomOnCooldownException
from .modals import (AddFieldModal, CommandEditModal, CustomTriggerModal,
                     EditAuthorModal, EditEmbedModal, EditFieldModal,
                     EditFooterModal, LoadMessageModal, TriggerEditModal)

if TYPE_CHECKING:

    from ..core import Xynus
    from .cogs import XynusCog
    from .context import XynusContext


emojis = Emojis()

class BaseView(_View):

    def __new__(cls, *args: Any, **kwargs: Any):
        self = super().__new__(cls)
        return self


    def __init__(
            self,
            timeout: Optional[int] = 120
    ):

        super().__init__(timeout=timeout)
        
        self.message: Optional[Message] = None

    
    async def on_timeout(self) -> None:
        return await _disable_all_items(self)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any]) -> None:
        bot: Xynus = interaction.client  # type: ignore
        kwargs = {
            "ephemeral": True
        }

        if isinstance(error, CustomOnCooldownException):
            kwargs["embed"] = ErrorEmbed(error.text)
        else:
            await bot.exceptions.add_error(
                error=error,
                ctx=interaction
            )
            kwargs["content"] = "🤔 Something went wrong"
        
        try:
            await (
                interaction.response.send_message
                if not interaction.response.is_done()
                else interaction.followup.send
            )(**kwargs)

        except HTTPException:
            pass # type: ignore




class Pagination(BaseView):
    def __init__(
            self,
            get_page: Callable,
            interaction: Optional[Interaction] = None,
            ctx: Optional[commands.Context] = None

    ):


        if interaction:
            self.reply = interaction.response.send_message
            self.user = interaction.user
            self.defer = interaction.response.defer
            self.message = interaction.original_response
        
        if ctx:
            self.reply = ctx.reply
            self.user = ctx.author
            self.defer = ctx.defer

        self.get_page = get_page
        self.total_pages: Optional[int] = None
        self.index = 0
        self.message = None

        super().__init__(timeout=120)



    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user == self.user:
            return True
        else:
            await interaction.response.edit_message()
            return False

    async def navegate(self, ephemeral: Optional[bool] = False):

        if ephemeral:
            await self.defer(ephemeral=True)

        kwrgs, self.total_pages = await self.get_page(self.index)

        self.update_buttons()
        
        if self.total_pages == 1:
            for item in self.children:
                if item.row == 0:
                    item.disabled = True
            

        
        msg = await self.reply(**kwrgs, view=self)

        if not self.message:
            self.message = msg
        else:
            self.message = await self.message()


    async def edit_page(self, interaction: Interaction):
        kwrgs, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await interaction.response.edit_message(**kwrgs, view=self)

    def update_buttons(self):
        
        self.children[0].disabled = self.index == 0
        self.children[1].disabled = self.index == 0

        self.children[2].label = "{} / {}".format(self.index + 1, self.total_pages)

        self.children[3].disabled = self.index == self.total_pages -1
        self.children[4].disabled = self.index == self.total_pages -1

    # @button(label="<<", style=ButtonStyle.blurple, disabled=True)
    @button(emoji=emojis.get("start"), style=ButtonStyle.blurple, disabled=True, row=0)
    async def start(self, interaction: Interaction, button: Button):
        self.index = 0

        await self.edit_page(interaction)

    # @button(label="<", style=ButtonStyle.blurple)
    @button(emoji=emojis.get("previous"), style=ButtonStyle.blurple, disabled=True, row=0)
    async def previous(self, interaction: Interaction, button: Button):
        self.index -= 1
        await self.edit_page(interaction)

    @button(label="1 / 1", style=ButtonStyle.grey, row=0)
    async def index_button(
        self,
        interaction: Interaction,
        button: Button
    ):
        from .modals import PaginationIndexModal

        modal = PaginationIndexModal(self)

        return await interaction.response.send_modal(modal)

    # @button(label=">", style=ButtonStyle.blurple)
    @button(emoji=emojis.get("next"), style=ButtonStyle.blurple, row=0)
    async def next(self, interaction: Interaction, button: Button):
        self.index += 1
        await self.edit_page(interaction)

    # @button(label=">>", style=ButtonStyle.blurple)
    @button(emoji=emojis.get("end"), style=ButtonStyle.blurple, row=0)
    async def end(self, interaction: Interaction, button: Button):
        self.index = self.total_pages -1
        await self.edit_page(interaction)
    

    async def on_timeout(self):
        await _disable_all_items(self)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1




class EmojisView(Pagination):

    def __init__(
            self,
            get_page: Callable,
            emojis_dict: Dict,
            interaction: Optional[Interaction] = None,
            ctx: Optional[commands.Context] = None,
    ):
        self.emojis = emojis_dict

        super().__init__(get_page, interaction, ctx)
    
    @button(label="Steal this one", style=ButtonStyle.green, emoji=emojis.get("hand"))
    async def add_emoji(
        self,
        interaction: Interaction,
        button: Button
    ):
        await interaction.response.defer(
            thinking=True
        )

        check_mark = emojis.get('checkmark')
        cross_mark = emojis.get('crossmark')

        emoji = self.emojis[self.index]
        url = "https://cdn.discordapp.com/emojis/{}.png".format(emoji.get("id"))
        async with ClientSession() as client:
            async with client.get(url) as resp:
                
                if not resp.status == 200:
                    return await interaction.edit_original_response(
                        content="{} | Failed to steal emoji `{}`: Invalid emoji data".format(
                            cross_mark,
                            emoji.get("name")
                        )
                    )
                
                data = await resp.read()
                
                

                try:
                    created_emoji = await interaction.guild.create_custom_emoji(
                        name=emoji.get("name"),
                        image=data
                    )
                
                    emoji = f"<:{created_emoji.name}:{created_emoji.id}>"

                    if created_emoji.animated:
                        emoji = f"<a:{created_emoji.name}:{created_emoji.id}>"


                    await interaction.edit_original_response(
                        content="{} | Successfully stole emoji: {}".format(
                            check_mark,
                            emoji
                        )
                    )

                except Forbidden:

                    await interaction.edit_original_response(
                        content="{} | Failed to create emoji `{}`: 403 error occured".format(
                            cross_mark,
                            emoji.get("name")
                        )
                    )

                except HTTPException as e:
                    if e.code == 30008:

                        await interaction.edit_original_response(
                            content="{} | Failed to steal emoji `{}`: The server has reached the maximum number of custom emojis".format(
                                cross_mark,
                                emoji.get("name")
                            )
                        )
                    
                    else:
                        await interaction.edit_original_response(
                            content="{} | Failed to steal emoji `{}`: {}".format(
                                cross_mark,
                                emoji.get("name"),
                                e.text
                            )
                        )

class DuplicatedMappingView(BaseView):
    
    def __init__(
            self,
            trigger: str,
            command: str,
            share_code: str,
            author: User,
            import_type: Literal["guild", "user"]
        ):



        self.command     = command
        self.trigger     = trigger
        self.share_code  = share_code
        self.author      = author
        self.import_type = import_type

        super().__init__(timeout=120)

    @select(
        options=[
            SelectOption(
                label="Create a new unique one",
                description="will create a new one with random characters appended.",
                value="unique"
            ),
            SelectOption(
                label="import with a new custom name",
                description="will create a new one with the name you specify.",
                value="specified"
            )
        ]
    )
    async def maps_select(
        self,
        inter: Interaction,
        select: Select
    ):
        value       = select.values[0]
        trigger     = self.trigger
        command     = self.command
        share_code  = self.share_code
        import_type = self.import_type

        if value == "specified":
            return await inter.response.send_modal(
                CustomTriggerModal(
                    trigger,
                    share_code,
                    command,
                    import_type
                )
            )

        encrypted_trigger = encrypt(trigger+random_string(5))
        if import_type == "user":
            target_id = inter.user.id
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
        elif import_type == "guild":
            target_id = inter.guild.id
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

        async with inter.client.pool.acquire() as conn:
            await conn.fetch(
                insertion_query,
                target_id,
                encrypted_trigger,
                int(time()),
                share_code
            )
        
        decrypted_trigger = decrypt(encrypted_trigger)
        inter.client._cmd_mapping_cache[target_id][decrypted_trigger] = command


        embed = Embed(
            color=inter.client.color,
            description=f"**Added {decrypted_trigger!r} to your mappings**"
        )

        await inter.response.edit_message(
            content=None,
            view=None,
            embed=embed
        )
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        
        if not interaction.user.id == self.author.id:
            await interaction.response.edit_message()
            return False
        
        return True


class MappingsImportView(BaseView):
    def __init__(
            self,
            share_code: str,
    ):
        
        self.share_code = share_code
        super().__init__(timeout=120)

    @button(
        label="Import",
        style=ButtonStyle.secondary,
        emoji="\N{INBOX TRAY}",
        custom_id="import-mapping"
    )
    async def import_button(
        self,
        inter: Interaction,
        btn: Button
    ):
        share_code = self.share_code

        if inter.guild and inter.user.guild_permissions.manage_guild:
            return await inter.response.send_message(
                content="Select an import method",
                view=MappingImportSelectView(
                    share_code
                ),
                ephemeral=True
            )
        
        conn = await inter.client.pool.acquire()

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
            await inter.client.pool.release(conn)
            return await inter.response.send_message(
                "Didn't find any mapping",
                ephemeral=True
            )
        
        trigger = decrypt(record["trigger"])
        command = decrypt(record["command"])

        data = inter.client.db._traverse_dict(
            inter.client._cmd_mapping_cache,
            [inter.user.id ,trigger],
            True
        )

        if data.get(trigger):
            view = DuplicatedMappingView(
                share_code=share_code,
                command=command,
                trigger=trigger,
                author=inter.user
            )

            return await inter.response.send_message(
                f"Trigger {trigger!r} already exists, so choose an option:",
                view=view,
                ephemeral=True
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
            inter.user.id,
            encrypted_trigger,
            int(time()),
            share_code
        )

        await inter.client.pool.release(conn)
        
        decrypted_trigger = decrypt(encrypted_trigger)
        inter.client._cmd_mapping_cache[inter.user.id][decrypted_trigger] = command
    
        await inter.response.send_message(
            f"**Added {decrypted_trigger!r} to your mappings**",
            ephemeral=True
        )

class MappingImportSelectView(BaseView):
    
    def __init__(
        self,
        share_code: str
    ):
        
        self.share_code = share_code
        super().__init__(timeout=120)

    @select(
        options=[
            SelectOption(
                label="Import for guild",
                value="guild"
            ),
            SelectOption(
                label="Import for yourself",
                value="user"
            )
        ]
    )
    async def import_for(
        self,
        inter: Interaction,
        select: Select
    ):
        value      = select.values[0]
        share_code = self.share_code

        conn = await inter.client.pool.acquire()
        if value == "user":

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
                await inter.client.pool.release(conn)
                return await inter.response.send_message(
                    "Didn't find any mapping",
                    ephemeral=True
                )
            
            trigger = decrypt(record["trigger"])
            command = decrypt(record["command"])

            data = inter.client.db._traverse_dict(
                inter.client._cmd_mapping_cache,
                [inter.user.id ,trigger],
                True
            )

            if data.get(trigger):
                view = DuplicatedMappingView(
                    share_code=share_code,
                    command=command,
                    trigger=trigger,
                    author=inter.user,
                    import_type=value
                )
                await inter.client.pool.release(conn)
                return await inter.response.edit_message(
                    content=f"Trigger {trigger!r} already exists, so choose an option:",
                    view=view,
                )

            encrypted_trigger = encrypt(trigger)

            
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
                inter.user.id,
                encrypted_trigger,
                int(time()),
                share_code
            )

            
            decrypted_trigger = decrypt(encrypted_trigger)
            inter.client._cmd_mapping_cache[inter.user.id][decrypted_trigger] = command
        
            await inter.response.edit_message(
                content=f"**Added {decrypted_trigger!r} to your mappings**",
            )
        elif inter.guild and value == "guild" and inter.user.guild_permissions.manage_guild:
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
                await inter.client.pool.release(conn)
                return await inter.response.send_message(
                    "Didn't find any mapping",
                    ephemeral=True
                )
            
            trigger = decrypt(record["trigger"])
            command = decrypt(record["command"])

            data = inter.client.db._traverse_dict(
                inter.client._cmd_mapping_cache,
                [inter.guild.id ,trigger],
                True
            )

            if data.get(trigger):
                view = DuplicatedMappingView(
                    share_code=share_code,
                    command=command,
                    trigger=trigger,
                    author=inter.user,
                    import_type=value
                )
                await inter.client.pool.release(conn)
                return await inter.response.edit_message(
                    content=f"Trigger {trigger!r} already exists, so choose an option:",
                    view=view,
                )

            encrypted_trigger = encrypt(trigger)

            
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
                inter.guild.id,
                encrypted_trigger,
                int(time()),
                share_code
            )

            
            decrypted_trigger = decrypt(encrypted_trigger)
            inter.client._cmd_mapping_cache[inter.guild.id][decrypted_trigger] = command
        
            await inter.response.edit_message(
                content=f"**Added {decrypted_trigger!r} to mappings**",
            )
        
        await inter.client.pool.release(conn)
            

class DynamicHelpView(Pagination):

    def __init__(
        self,
        client: commands.Bot,
        prefix: Union[str, Sequence[str]],
        bot_commands: Sequence[commands.Command],
        cogs: Dict[str, commands.Cog],
        ctx: Optional[commands.Context] = None,
        interaction: Optional[Interaction] = None,
    ) -> None:
        
        main_embed = DynamicHelpEmbed(
            client=client,
            ctx=ctx,
            interaction=interaction,
            prefix=prefix,
            commands=bot_commands,
        )

        main_embed.set_author(
            name=f"Xynus - V{version}"
        )

        new_cogs = {}
        for cog_name in cogs:

            if cogs[cog_name].get_commands() != []:
                new_cogs[cog_name] = cogs[cog_name]

        cogs = new_cogs

        first_cog = cogs[[*cogs][0]]
        self.cog = first_cog

        self.home = True
        self.ctx = ctx

        async def get_page(
                index: int,
                cog: commands.Cog
        ): 
            _commands = _get_all_commands(cog=cog)
            name = cog.__cog_name__

            chunks = _chunker(_commands, 10)

            embed = CommandsEmbed(
                commands=chunks[index],
                title=f"Category: {name}",
                prefix=prefix[0],
                total_commands=len(_commands)
            )

            kwrgs = {
                "embed": embed
            }
            total_pages = len(chunks)
            if self.home:

                kwrgs = {
                    "embed": main_embed,
                }
                total_pages = 1
                self.home = False

            return kwrgs, total_pages

        super().__init__(
            get_page=get_page,
            ctx=ctx,
            interaction=interaction
        )

        self.add_item(
            self.DynamicHelpSelect(
                cogs=cogs
            )
        )

    async def edit_page(self, interaction: Interaction):

        kwrgs, self.total_pages = await self.get_page(self.index, self.cog)
        self.update_buttons()
        await interaction.response.edit_message(**kwrgs, view=self)


    async def navegate(self, ephemeral: Optional[bool] = False):

        
        kwrgs, self.total_pages = await self.get_page(self.index, self.cog)

        self.update_buttons()
        
        if self.total_pages == 1:

            for item in self.children:
                if item.row == 0:
                    item.disabled = True
            

        
        msg = await self.reply(**kwrgs, view=self, ephemeral=ephemeral)

        if not self.message:
            self.message = msg
        else:
            self.message = await self.message()

    class DynamicHelpSelect(_Select):
        def __init__(
                self,
                cogs: Sequence[commands.Cog]
        ) -> None:

            self.cogs = cogs

            self.cog_values = {}

            for i in range(len([*cogs])):
                self.cog_values[f"cog_{i}"] = [*cogs][i]

            cog_emojis = [self.cogs[cog].emoji for cog in self.cogs]

            options = [
                SelectOption(
                    label="Main Page",
                    value="home",
                    emoji=emojis.get("house")
                )
            ]

            options+=[
                SelectOption(
                    label=label,
                    value=value,
                    emoji=emoji
                )

                for label, value, emoji in zip(self.cogs, [*self.cog_values], cog_emojis)
            ]


            super().__init__(
                options=options,
                custom_id="helpselect",
                placeholder="Choose a category please"
            )
        async def callback(self, interaction: Interaction) -> Any:

            value = self.values[0]

            if value == "home":
                self.view.home = True
                return await self.view.edit_page(interaction)

            cog_name = self.cog_values[value]
            cog = self.cogs[cog_name]

            self.view.cog = cog
            self.view.index = 0
            await self.view.edit_page(interaction)

class ConfirmationView(_View):

    def __init__(
            self,
            ctx: "XynusContext", 
            *, 
            owner_id: Optional[int] = None, 
            timeout: int = 60
    ):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id or ctx.author.id
        self.ctx = ctx
        self.value = None
        self.message: Message | None = None


        super().__init__(timeout=120)

    async def interaction_check(self, interaction: Interaction) -> bool:
        
        if self.owner_id == interaction.user.id:
            return True
        
        await interaction.response.edit_message()
        return False

    @button(
        label="Yes",
        style=ButtonStyle.green,
        custom_id="yes",
    )
    async def yes(
        self,
        interaction: Interaction,
        button: Button
    ): 
        await interaction.response.defer()
        self.value = True

        await interaction.delete_original_response()
        self.stop()
    
        
    
    @button(
        label="No",
        style=ButtonStyle.red,
        custom_id="no" 
    )
    async def no(
        self,
        interaction: Interaction,
        button: Button
    ):
        await interaction.response.edit_message(
            view=None,
            embed=Embed(
                color=self.ctx.client.color,
                description="**Action cancelled!**"
            )
        )
        self.value = False
        self.stop()
    
    async def on_timeout(self) -> None:
        self.stop()
        if self.message:
            return await self.message.edit(
                view=None,
                embed=Embed(
                    description="**Action cancelled (Timeout)**",
                    color=self.ctx.client.color
                )
            )


class WhisperView(_View):

    def __init__(
            self,
            target: User,
            author: User,
            text: str
    ):
        self.message = None
        self.target = target
        self.author = author
        self.text = text


        super().__init__(
            timeout=15 * 60
        )

    @button(
            label="Show Message",
            style=ButtonStyle.secondary,
            emoji="🤨"
    )
    async def show_message(
        self,
        inter: Interaction,
        button: Button
    ):
        
        await inter.response.send_message(
            content=(
                f"**Sent from {self.author.mention}**\n"
                f"{self.text}"
            ),
            ephemeral=True
        )

        await inter.message.delete()

    async def interaction_check(self, interaction: Interaction) -> bool:
        
        if self.target.id == interaction.user.id:
            return True
        
        await interaction.response.edit_message()
        return False

    async def on_timeout(self) -> None:
        return await _disable_all_items(self)


class WhisperModalView(_View):
    
    def __init__(
            self,
            target: User,
            author: User
    ):
        
        self.message = None

        self.target = target
        self.author = author
        
        super().__init__(
            timeout=120,
        )
    

    async def on_timeout(self) -> None:
        return await _disable_all_items(self)


    @button(
        label="Enter your message",
        style=ButtonStyle.secondary
    )
    async def enter_your_message(
        self,
        inter: Interaction,
        button: Button
    ):
        from .modals import WhisperModal
        
        return await inter.response.send_modal(
            WhisperModal(
                target=self.target
            )
        )

    
    async def interaction_check(self, interaction: Interaction) -> bool:
        
        if self.author.id == interaction.user.id:
            return True
        
        await interaction.response.edit_message()
        return False

class MappingView(BaseView):

    def __init__(
        self,
        author: User,
        command: str,
        trigger: str,
        created_at: int,
        mappings: commands.Command,
        mode: Literal["guild", "user"]
    ):
        super().__init__(timeout=120)
        
        self.mode       = mode
        self.author     = author
        self.command    = command
        self.trigger    = trigger
        self.mappings   = mappings
        self.created_at = created_at

        self.add_item(DeleteButton())


    @button(
        emoji=emojis.get("pencil"),
        custom_id="edit_mapping"
    )
    async def edit_mapping(
        self,
        inter: Interaction,
        btn: Button
    ):
        await inter.response.edit_message(
            view=MappingEditView(
                self.command, 
                self.trigger,
                self,
                self.author,
                self.mode
            )
        )

class MappingEditView(BaseView):

    def __init__(
        self,
        command: str,
        trigger: str,
        prev_view: "MappingView",
        author: User,
        mode: Literal["guild", "user"]
    ):
        self.mode      = mode 
        self.author    = author
        self.command   = command
        self.trigger   = trigger
        self.prev_view = prev_view

        super().__init__(timeout=120)
    
    @select(
        options=[
            SelectOption(
                label="Edit command",
                emoji=emojis.get("pencil"),
                value="command"
            ),
            SelectOption(
                label="Edit trigger",
                emoji=emojis.get("pencil"),
                value="trigger"
            )
        ]
    )
    async def edit_select(
        self,
        inter: Interaction,
        select: Select
    ):

        if select.values[0] == "trigger":
            modal = TriggerEditModal(
                self,
                self.mode
            )
        
        elif select.values[0] == "command":
            modal = CommandEditModal(
                self
            )
        
        await inter.response.send_modal(modal)
        

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not interaction.user.id == self.author.id:
            await interaction.response.edit_message()
            return False
        return True

    @button(
        label="Save",
        emoji="\N{FLOPPY DISK}",
        style=ButtonStyle.green,
        disabled=True
    )
    async def save_button(
        self,
        inter: Interaction,
        btn: Button
    ):
        
        if self.mode == "user":
            target_id = inter.user.id
            query = """
            UPDATE mappings
            SET 
                trigger = $1,
                command = $2
            WHERE 
                user_id = $3
            AND 
                trigger = $4;
            """
        elif self.mode == "guild":
            target_id = inter.guild.id
            query = """
            UPDATE mappings
            SET 
                trigger = $1,
                command = $2
            WHERE 
                guild_id = $3
            AND 
                trigger = $4;
            """

        cached_maps: Dict[str, Any] = inter.client.db._traverse_dict(
            inter.client._cmd_mapping_cache,
            keys=[target_id],
            create_missing=True
        ).get(target_id)

        if len(tuple(cached_maps.items())) > 30 and \
                not await inter.client.is_owner(inter.user):
            embed = Embed(
                description=f"Sorry but you can't add more than 30 mappings",
                color=inter.client.color
            )
            return await inter.response.send_message(
                embed=embed,
                delete_button=True
            )

        del inter.client._cmd_mapping_cache[target_id][self.prev_view.trigger]
        prev_trigger = self.prev_view.trigger
        self.prev_view.trigger = self.trigger
        self.prev_view.command = self.command
        inter.client._cmd_mapping_cache[target_id][self.trigger] = self.command


        async with inter.client.pool.acquire() as conn:
            await conn.execute(
                query, 
                encrypt(self.trigger),
                encrypt(self.command),
                target_id,
                encrypt(prev_trigger)
            )

        return await inter.response.edit_message(
            view=self.prev_view,
            embed=MappingInfoEmbed(
                inter,
                command=self.command,
                trigger=self.trigger,
                created_at=self.prev_view.created_at,
            )
        )

    def update_save_button(self):
        self.save_button.disabled = (
                self.command == self.prev_view.command
                and self.trigger == self.prev_view.trigger
            )

    @button(
        label="Go back",
        style=ButtonStyle.secondary
    )
    async def go_back(
        self,
        inter: Interaction,
        btn: Button
    ):

        return await inter.response.edit_message(
            view=self.prev_view,
            embed=MappingInfoEmbed(
                inter,
                self.prev_view.trigger,
                self.prev_view.command,
                self.prev_view.created_at
            )
        )


    async def on_timeout(self) -> None:
        return await _disable_all_items(self)

class ViewWithDeleteButton(BaseView):
    """A view that includes a DeleteButton."""


    def __init__(
            self,
            author: User,
            /, 
            *,
            timeout: Optional[int] = 30
    ):
        from .buttons import DeleteButton

        self.message = None

        super().__init__(
            timeout=timeout
        )

        self.author = author

        self.add_item(
            DeleteButton()
        )
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        
        if self.author.id == interaction.user.id:
            return True
        
        await interaction.response.edit_message()
        return False

    async def on_timeout(self) -> None:
        return await _disable_all_items(self)


class SendToView(BaseView):
    def __init__(self, *, parent: "EmbedEditor"):
        self.parent = parent
        super().__init__(timeout=300)

    @select(
        cls=ChannelSelect,
        channel_types=[
            ChannelType.text,
            ChannelType.news,
            ChannelType.voice,
            ChannelType.private_thread,
            ChannelType.public_thread,
        ],
    )
    async def pick_a_channel(self, interaction: Interaction, select: ChannelSelect):
        await interaction.response.defer(ephemeral=True)
        channel = select.values[0]
        if not isinstance(interaction.user, Member) or not interaction.guild:
            return await interaction.followup.send(
                'for some reason, discord thinks you are not a member of this server...', ephemeral=True
            )
        channel = interaction.guild.get_channel_or_thread(channel.id)
        if not isinstance(channel, Messageable):
            return await interaction.followup.send('That channel does not exist... somehow.', ephemeral=True)
        if not channel.permissions_for(interaction.user).send_messages:
            return await interaction.followup.send('You cannot send messages in that channel.', ephemeral=True)
        await channel.send(embed=self.parent.embed)
        await interaction.delete_original_response()
        await interaction.followup.send('Sent!', ephemeral=True)
        self.stop()

    @button(label='Go Back')
    async def stop_pages(self, interaction: Interaction, button: Button):
        """stops the pagination session."""
        await interaction.response.edit_message(embed=self.parent.current_embed, view=self.parent)
        self.stop()

    async def on_timeout(self) -> None:
        if self.parent.message:
            try:
                await self.parent.message.edit(view=self.parent)
            except NotFound:
                pass

class FieldSelectorView(BaseView):
    def __init__(self, parent_view: "EmbedEditor"):
        self.parent = parent_view
        super().__init__(timeout=300)
        self.update_options()

    def update_options(self):
        self.pick_field.options = []
        for i, field in enumerate(self.parent.embed.fields):
            self.pick_field.add_option(label=f"{i + 1}) {(field.name or '')[0:95]}", value=str(i))

    @select(placeholder='Select a field to delete.')
    async def pick_field(self, interaction: Interaction, select: Select):
        await self.actual_logic(interaction, select)

    @button(label='Go back')
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(view=self.parent)
        self.stop()

    async def actual_logic(self, interaction: Interaction, select: Select) -> None:
        raise NotImplementedError('Child classes must overwrite this method.')

class DeleteFieldWithSelect(FieldSelectorView):
    async def actual_logic(self, interaction: Interaction, select: Select[Self]):
        index = int(select.values[0])
        self.parent.embed.remove_field(index)
        await self.parent.update_buttons()
        await interaction.response.edit_message(embed=self.parent.current_embed, view=self.parent)
        self.stop()

class EditFieldSelect(FieldSelectorView):
    async def actual_logic(self, interaction: Interaction, select: Select[Self]):
        index = int(select.values[0])
        self.parent.timeout = 600
        await interaction.response.send_modal(EditFieldModal(self.parent, index))

class EmbedEditor(BaseView):
    def __init__(self, owner: Member, cog: "XynusCog", *, timeout: Optional[float] = 600):
        self.owner: Member = owner
        self.cog = cog
        self.embed = Embed()
        self.showing_help = False
        self.message: Optional[Message] = None
        super().__init__(timeout=timeout)
        self.clear_items()
        self.add_items()

    @staticmethod
    def shorten(_embed: Embed):
        embed = Embed.from_dict(deepcopy(_embed.to_dict()))
        while len(embed) > 6000 and embed.fields:
            embed.remove_field(-1)
        if len(embed) > 6000 and embed.description:
            embed.description = embed.description[: (len(embed.description) - (len(embed) - 6000))]
        return embed

    @property
    def current_embed(self) -> Embed:
        if self.showing_help:
            return self.help_embed()
        if self.embed:
            if len(self.embed) < 6000:
                return self.embed
            else:
                return self.shorten(self.embed)
        return self.help_embed()

    async def interaction_check(self, interaction: Interaction, /):  # pyright: ignore[reportIncompatibleMethodOverride]
        if interaction.user == self.owner:
            return True
        await interaction.response.send_message('This is not your menu.', ephemeral=True)
        return False

    def add_items(self):
        """This is done this way because if not, it would get too cluttered."""
        # Row 1
        self.add_item(Btn(label='Edit:', style=ButtonStyle.blurple, disabled=True))
        self.add_item(EditWithModalButton(EditEmbedModal, label='Embed', style=ButtonStyle.blurple))
        self.add_item(EditWithModalButton(EditAuthorModal, row=0, label='Author', style=ButtonStyle.blurple))
        self.add_item(EditWithModalButton(EditFooterModal, row=0, label='Footer', style=ButtonStyle.blurple))
        self.add_item(DeleteButton())
        # Row 2
        self.add_item(Btn(row=1, label='Fields:', disabled=True, style=ButtonStyle.blurple))
        self.add_fields = EditWithModalButton(AddFieldModal, row=1, emoji='\N{HEAVY PLUS SIGN}', style=ButtonStyle.green)
        self.add_item(self.add_fields)
        self.add_item(self.remove_fields)
        self.add_item(self.edit_fields)
        # Row 3
        self.add_item(self.send)
        self.add_item(self.send_to)
        self.add_item(self.load_message)
        self.add_item(self.help_page)
        # Row 4
        self.character_count: button = Btn(row=3, label='0/6,000 Characters', disabled=True)
        self.add_item(self.character_count)
        self.fields_count: button = Btn(row=3, label='0/25 Total Fields', disabled=True)
        self.add_item(self.fields_count)

    async def update_buttons(self):
        fields = len(self.embed.fields)
        if fields > 25:
            self.add_fields.disabled = True
        else:
            self.add_fields.disabled = False
        if not fields:
            self.remove_fields.disabled = True
            self.edit_fields.disabled = True
        else:
            self.remove_fields.disabled = False
            self.edit_fields.disabled = False
            self.help_page.disabled = True
        if self.embed:
            if len(self.embed) <= 6000:
                self.send.style = ButtonStyle.green
                self.send_to.style = ButtonStyle.green
            else:
                self.send.style = ButtonStyle.red
                self.send_to.style = ButtonStyle.red
            self.help_page.disabled = False
        else:
            self.send.style = ButtonStyle.red
            self.send_to.style = ButtonStyle.red

        self.character_count.label = f"{len(self.embed)}/6,000 Characters"
        self.fields_count.label = f"{len(self.embed.fields)}/25 Total Fields"

        if self.showing_help:
            self.help_page.label = 'Show My Embed'
        else:
            self.help_page.label = 'Show Help Page'

    def help_embed(self) -> Embed:
        embed = Embed(
            title='__`M⬇`__ This is the embed title',
            color=self.cog.client.color,
            description=(
                "__`M⬇`__ This is the embed description. This field "
                "**supports** __*Mark*`Down`__, which means you can "
                "use features like ~~strikethrough~~, *italics*, **bold** "
                "and `mono`, and they will be rendered!"
                "\nText that supports MarkDown have this: __`M⬇`__"
            ),
            url='https://this-is.the/title-url',
        )
        embed.add_field(name='__`M⬇`__ This is a field name.', value='and this is the value. This field is in-line.')
        embed.add_field(name='Fields per line?', value='you can have up to **3** fields in a single line!')
        embed.add_field(
            name='Here is another field, but not in-line',
            value='Fields can have up to 256 characters in the name of a field, and up to 1,024 characters in the value!',
            inline=False,
        )
        embed.add_field(
            name='How do I use this interface?',
            value=(
                'To edit parts of the embed, you just use the buttons that appear below.'
                ' I will tell you if anything you put was not valid. Leaving a text field '
                'empty will make that field be removed.'
            ),
        )
        embed.set_author(
            name='This is the author of the embed',
            icon_url='https://cdn.duck-bot.com/file/AVATAR',
            url='https://this-is.the/author-url',
        )
        embed.set_image(url='https://cdn.duck-bot.com/file/IMAGE')
        embed.set_thumbnail(url='https://cdn.duck-bot.com/file/THUMBNAIL')
        footer_text = "This is the footer, which like the author, does not support markdown."
        if not self.embed and not self.showing_help:
            footer_text += '\n💢This embed will be replaced by yours once it has characters💢'
        embed.set_footer(icon_url='https://cdn.duck-bot.com/file/ICON', text=footer_text)
        return embed

    @button(row=1, emoji='\N{HEAVY MINUS SIGN}', style=ButtonStyle.red, disabled=True)
    async def remove_fields(self, interaction: Interaction, button: button):
        await interaction.response.edit_message(view=DeleteFieldWithSelect(self))

    @button(row=1, emoji="✏️", disabled=True, style=ButtonStyle.green)
    async def edit_fields(self, interaction: Interaction, button: button):
        await interaction.response.edit_message(view=EditFieldSelect(self))


    @button(label='Send', row=2, style=ButtonStyle.red)
    async def send(self, interaction: Interaction, button: button):
        if not self.embed:
            return await interaction.response.send_message('Your embed is empty!', ephemeral=True)
        elif len(self.embed) > 6000:
            return await interaction.response.send_message(
                'You have exceeded the embed character limit (6000)', ephemeral=True
            )
        await interaction.channel.send(embed=self.embed)  # type: ignore
        await interaction.response.defer()
        await interaction.delete_original_response()

    @button(label='Send To', row=2, style=ButtonStyle.red)
    async def send_to(self, interaction: Interaction, button: button):
        if not self.embed:
            return await interaction.response.send_message('Your embed is empty!', ephemeral=True)
        elif len(self.embed) > 6000:
            return await interaction.response.send_message(
                'You have exceeded the embed character limit (6000)', ephemeral=True
            )
        await interaction.response.edit_message(view=SendToView(parent=self))

    @button(
        label="Load Message", 
        row=2,
        style=ButtonStyle.gray
    )
    async def load_message(
        self,
        interaction: Interaction,
        button: Button
    ):
        
        await interaction.response.send_modal(LoadMessageModal(self))

    @button(label='Show Help Page', row=2, disabled=True)
    async def help_page(self, interaction: Interaction, button: button):
        self.showing_help = not self.showing_help
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.current_embed, view=self)

    async def on_timeout(self) -> None:
        await _disable_all_items(self)


class FieldSelectorView(BaseView):
    def __init__(self, parent_view: EmbedEditor):
        self.parent = parent_view
        super().__init__(timeout=300)
        self.update_options()

    def update_options(self):
        self.pick_field.options = []
        for i, field in enumerate(self.parent.embed.fields):
            self.pick_field.add_option(label=f"{i + 1}) {(field.name or '')[0:95]}", value=str(i))

    @select(placeholder='Select a field.')
    async def pick_field(self, interaction: Interaction, select: Select):
        await self.actual_logic(interaction, select)

    @button(label='Go back')
    async def cancel(self, interaction: Interaction, button: button):
        await interaction.response.edit_message(view=self.parent)
        self.stop()

    async def actual_logic(self, interaction: Interaction, select: Select[Self]) -> None:
        raise NotImplementedError('Child classes must overwrite this method.')



class TicketOpenView(BaseView):

    def __init__(
            self,
            data: Dict[str, Any],
    ):
        
        options = [
            SelectOption(
                label=decrypt(value.get("panel_name")),
                value=name,
                emoji=value.get("emoji")
            )

            for name, value in data.items()
            
        ]

        super().__init__(
            timeout=120
        )

        self.add_item(
            self.TicketSelect(
                options=options
            )
        )



    class TicketSelect(_Select):

        def __init__(
                self,
                **kwrgs

        ) -> None:
            super().__init__(
                **kwrgs,
                max_values=1,
                min_values=1
            )
        
        async def callback(
                self, 
                inter: Interaction
        ) -> Any:
            

            uuid = self.values[0]

            pool: Pool = inter.client.pool
            db: KVDatabase = inter.client.db

            data: Optional[Dict[str, Any]] = await db.get(f"{inter.guild.id}.settings.tickets.{uuid}")

            kwrgs = {
                "username": inter.user.name,
                "userid": inter.user.id,
                "usermention": inter.user.mention,
                "panelname": decrypt(data.get("panel_name")),
                "panelemoji": data.get("emoji") or ""
            }




            decrypted_opened_name_format = decrypt(data.get("opened_name_format"))
            name = Template(decrypted_opened_name_format).safe_substitute(
                **kwrgs   
            )

            category = inter.client.get_channel(data.get("opened_category_id"))

            if category and not category.permissions_for(inter.guild.me).manage_channels:
                category = None
                

            overwrites = {
                inter.guild.default_role: PermissionOverwrite(
                    view_channel = False,
                    send_messages = False
                ),
                inter.user: PermissionOverwrite(
                    view_channel = True,
                    send_messages = True
                )
            }

            for role_id in data.get("supporter_roles"):
                
                role = inter.guild.get_role(role_id)

                if role and role.position <= inter.guild.me.top_role.position:
                    overwrites[role] = PermissionOverwrite(
                        view_channel = True,
                        send_messages = True
                    )



            ticket = await inter.guild.create_text_channel(
                name=name,
                overwrites=overwrites,
                category=category
            )

            decrypted_closed_name_format = decrypt(data.get("closed_name_format")) or ticket.name + "-closed"


            kwrgs = {
                "username": inter.user.name,
                "userid": inter.user.id,
                "usermention": inter.user.mention,
                "panelname": decrypt(data.get("panel_name")),
                "lastname": ticket.name,
            }

            decrypted_closed_name = Template(decrypted_closed_name_format).safe_substitute(
                **kwrgs
            )

            query = inter.client._load_query("set_ticket.sql")

            args = (
                inter.guild.id,
                inter.user.id,
                ticket.id,
                [], # Empty user ids.
                True, 
                True, # valid until get closed.
                uuid,
                encrypt(decrypted_closed_name[:100:])
            )


            async with pool.acquire() as conn:
                await conn.execute(query, *args)
            await inter.edit_original_response(
                content=f"Created your ticket {ticket.mention}",
                view=None
            )

            kwrgs["channelname"] = ticket.name
            kwrgs["channelmention"] = ticket.mention

            decrypted_message = decrypt(data.get("opened_message_content"))

            content = Template(decrypted_message).safe_substitute(
                **kwrgs
            )

            await ticket.send(
                content=content,
                view=PersistentViews.TicketClose(
                    inter.client
                )
            )


        
        async def interaction_check(
                self, 
                interaction: Interaction
        ) -> bool:
            await interaction.response.defer(
                ephemeral=True,
            )
        
            query = """
            SELECT channel_id 
            FROM tickets 
            WHERE owner_id = $1 
            AND guild_id = $2
            AND is_open = TRUE 
            AND is_valid = TRUE;
            """
    

            async with interaction.client.pool.acquire() as conn:
                results = await conn.fetch(
                    query, 
                    interaction.user.id, 
                    interaction.guild.id
                )


            if results:
                await interaction.edit_original_response(
                    content="You aleardy have a ticket",
                    view=None
                )
                return False
            
            return True
            


            

class PersistentViews:

    def __init__(self, client: commands.Bot) -> None:

        self.ticket_edit_cd = commands.CooldownMapping.from_cooldown(2, 10 * 60, lambda interaction: interaction.channel)
        self.client = client

    
    class GuildJoinedView(BaseView):
        def __init__(
                self, 
                client: commands.Bot
        ):

            self.client = client


            super().__init__(
                timeout=None
            )
    

        def _find_guild(
                self,
                message_content: str,
                /
        ):
            
            pattern = r"ID\*\*:\s*`(\d+)`"

            content_search = _search(
                pattern=pattern,
                string=message_content
            )

            guild_id = content_search.group(1)

            if guild_id:
                return self.client.get_guild(int(guild_id))
            
            return guild_id

        @button(
            label="Generate Invite link",
            custom_id="gen-invite",
            style=ButtonStyle.gray,
            emoji="➕",
        )
        async def gen_invite(
            self,
            inter: Interaction,
            btn: Button
        ):
            await inter.response.defer(
                thinking=True,
                ephemeral=True
            )


            guild = self._find_guild(inter.message.content)


            if not guild:
                return await inter.edit_original_response(
                    content=f"{emojis.get('crossmark')} | Didn't find this guild",
                )
            
            

            accessable_channels = [
                *filter(
                    lambda channel: channel.permissions_for(guild.me).create_instant_invite and channel.type != ChannelType.category, 
                    guild.channels
                )
            ]

            if not accessable_channels:
                return await inter.edit_original_response(
                    content=f"{emojis.get('crossmark')} | I don't have permission to create invite from guild."
                )
            
            channel = accessable_channels[0]

            invite_link = await channel.create_invite(
                reason=f"For {self.client.user.name}'s developers."
            )

            await inter.edit_original_response(
                content=f"{emojis.get('checkmark')} | {invite_link} - Channel: `#{channel.name}`"
            )


        @button(
            label="Leave this guild",
            custom_id="leave-guild",
            style=ButtonStyle.danger
        )
        async def leave_guild(
            self,
            inter: Interaction,
            btn: Button
        ):
            
            await inter.response.defer(
                thinking=True,
                ephemeral=True
            )


            guild = self._find_guild(inter.message.content)


            if not guild:
                return await inter.edit_original_response(
                    content=f"{emojis.get('crossmark')} | Didn't find this guild",
                )
            try:
                await guild.leave()
                await inter.edit_original_response(
                    content=f"{emojis.get('checkmark')} | Leaved `{guild.name}`"
                )
            
            except HTTPException:

                await inter.edit_original_response(
                    content=f"{emojis.get('crossmark')} | Failed to leave `{guild.name}`"
                )

        async def interaction_check(
                self, 
                interaction: Interaction
        ) -> bool:
            
            if not await self.client.is_owner(interaction.user):
                await interaction.response.edit_message()
                return False
            
            return True
        
    
    class TicketCreateView(BaseView):
        def __init__(
                self,
                client: commands.Bot
        ):
            self.client = client
            self.pool: Pool = client.pool

            super().__init__(
                timeout=None
            )

        @button(
            label="Create a ticket",
            custom_id="ticket-create"
        )
        async def ticket_create(
            self,
            inter: Interaction,
            btn: Button
        ):
            data = await self.client.db.get(f"{inter.guild.id}.settings.tickets")
            
            if not data:
                return await inter.edit_original_response(
                    content="Didn't find any ticket panel in this server"
                )

            await inter.edit_original_response(
                content="نه",
                view=TicketOpenView(
                    data=data
                )
            )
            
        async def interaction_check(
                self, 
                interaction: Interaction
        ) -> bool:
            await interaction.response.defer(
                ephemeral=True,
                thinking=True
            )
        
            query = """
            SELECT channel_id 
            FROM tickets 
            WHERE owner_id = $1 
            AND guild_id = $2
            AND is_open = TRUE 
            AND is_valid = TRUE;
            """
    

            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    query, 
                    interaction.user.id, 
                    interaction.guild.id
                )


            if results:
                await interaction.edit_original_response(
                    content="You already have a ticket"
                )
                return False
            
            return True
            


    class TicketClose(BaseView):
        def __init__(
                self,
                client: commands.Bot
        ):
            self.client = client
            self.pool: Pool = client.pool

            super().__init__(
                timeout=None
            )

        @button(
            label="Close",
            custom_id="ticket-close",
            emoji=emojis.get("lock")
        )
        @ticket_edit_cooldown
        async def ticket_close(
            self,
            inter: Interaction,
            btn: Button
        ):
            ticket = inter.channel

            if not ticket.permissions_for(inter.guild.me).manage_channels:
                return await inter.edit_original_response(
                    content="I don't have permission to do that."
                )

            query = """
            SELECT *
            FROM tickets
            WHERE channel_id = $1
            AND is_open = TRUE;
            """
            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    query,
                    ticket.id
                )


            result = results[0]


            owner_id = result["owner_id"]
            user_ids = result["user_ids"]
            panel_id = result["panel_id"]
            encrypted_original_name = result["original_name"]
            original_name = decrypt(encrypted_original_name)

            data = await inter.client.db.get(f"{inter.guild.id}.settings.tickets.{panel_id}")

            

            overwrites = {
                inter.guild.default_role: PermissionOverwrite(
                    view_channel = False,
                    send_messages = False
                )
            }

            for user_id in user_ids:
                
                if inter.guild.get_member(user_id):
                    overwrites[Object(id=user_id)] = PermissionOverwrite(
                        view_channel = False,
                        send_messages = False
                    )

            if inter.guild.get_member(owner_id):

                overwrites[Object(id=owner_id)] = PermissionOverwrite(
                    send_messages = False,
                    view_channel = False
                )
                

            data = await inter.client.db.get(f"{inter.guild_id}.settings.tickets.{panel_id}")

            category = inter.client.get_channel(data.get("closed_category_id"))

            if category and not category.permissions_for(inter.guild.me).manage_channels:
                category = None
            

            await ticket.edit(
                overwrites=overwrites,
                name=original_name,
                category=category
            )

            args = (
                inter.guild.id,
                owner_id,
                ticket.id,
                user_ids,
                False, 
                False,
                panel_id,
                encrypted_original_name
            )

            query = self.client._load_query("set_ticket.sql")
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    *args
                )


            await inter.edit_original_response(
                content="👍️"
            )

            await inter.channel.send(
                content=f"Closed by {inter.user.mention}.",
                view=PersistentViews.ClosedTicketView(
                    self.client
                )
            )
        
        async def interaction_check(
                self, 
                interaction: Interaction
        ) -> bool:
            await interaction.response.defer(
                thinking=True,
                ephemeral=True
            )

            query = """
            SELECT *
            FROM tickets
            WHERE channel_id = $1
            AND is_open = TRUE;
            """

            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    query,
                    interaction.channel.id
                )

            if not results:
                await interaction.edit_original_response(
                    content="This ticket is already closed."
                )
                return False
            
            return True

        async def on_error(
                self, 
                interaction: Interaction, 
                error: Exception, 
                item: Item[Any]
        ) -> None:
            
            if isinstance(error, CustomOnCooldownException):

                embed = ErrorEmbed(
                    "Due to prevent discord rate limits, this action is on cooldown. You can retry after "
                    f"{error.retry_after} second{'' if error.retry_after < 2 else 's'}"
                )


            await (
                interaction.response.send_message 
                if not interaction.response.is_done() 
                else interaction.followup.send
            )(
                embed=embed,
                ephemeral=True
            )
    
    class ClosedTicketView(_View):

        def __init__(
                self,
                client: commands.Bot
        ):
            self.client = client
            self.pool: Pool = self.client.pool

            super().__init__(
                timeout=None
            )


        @button(
            label="Delete",
            style=ButtonStyle.gray,
            emoji=emojis.get("trashcan"),
            custom_id="ticket-delete"
        )
        async def delete(
            self,
            inter: Interaction,
            btn: Button
        ):
            
            await inter.followup.send(
                content="👍️",
                ephemeral=True
            )

            await inter.channel.send(
                content="🚧 *This ticket will be deleted soon.*"
            )


            try:
                await sleep(5)
                await inter.channel.delete(
                    reason=f"Deleted by {inter.user.name} | {inter.user.id}"
                )

            except (HTTPException, Forbidden):
                pass

            query = """
            DELETE FROM tickets
            WHERE channel_id = $1
            AND guild_id = $2;
            """

            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    inter.channel_id,
                    inter.guild_id
                )


            
        @button(
                label="reopen",
                custom_id="ticket-reopen",
                emoji=emojis.get("unlock")
        )
        @ticket_edit_cooldown
        async def reopen(
            self,
            inter: Interaction,
            btn: Button
        ):
            ticket = inter.channel

            if not ticket.permissions_for(inter.guild.me).manage_channels:
                return await inter.edit_original_response(
                    content="I don't have permission to do that."
                )

            query = """
            SELECT *
            FROM tickets
            WHERE channel_id = $1
            AND is_open = FALSE;
            """
            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    query,
                    ticket.id
                )


            result = results[0]


            owner_id = result["owner_id"]
            user_ids = result["user_ids"]
            panel_id = result["panel_id"]

            data = await inter.client.db.get(f"{inter.guild.id}.settings.tickets.{panel_id}")

            

            overwrites = {
                inter.guild.default_role: PermissionOverwrite(
                    view_channel = False,
                    send_messages = False
                )
            }

            for user_id in user_ids:
                
                if inter.guild.get_member(user_id):
                    overwrites[Object(id=user_id)] = PermissionOverwrite(
                        view_channel = True,
                        send_messages = True
                    )

            if inter.guild.get_member(owner_id):

                overwrites[Object(id=owner_id)] = PermissionOverwrite(
                    send_messages = True,
                    view_channel = True
                )
                

            data = await inter.client.db.get(f"{inter.guild_id}.settings.tickets.{panel_id}")

            category = inter.client.get_channel(data.get("opened_category_id"))

            if category and not category.permissions_for(inter.guild.me).manage_channels:
                category = None

            decrypted_opened_name = decrypt(data.get("opened_name_format")) or ticket.name
            
            
            user = await inter.client.fetch_user(owner_id)
            kwrgs = {
                "username": user.name,
                "userid": user.id,
                "usermention": user.mention,
                "panelname": decrypt(data.get("panel_name")),
                "lastname": ticket.name,
                "panelemoji": data.get("emoji") or ""
            }

            opened_name_format = Template(decrypted_opened_name).safe_substitute(
                **kwrgs
            )

            await ticket.edit(
                overwrites=overwrites,
                name=opened_name_format,
                category=category
            )

            args = (
                inter.guild.id,
                owner_id,
                ticket.id,
                user_ids,
                True, 
                False,
                panel_id,
                encrypt(opened_name_format)
            )

            query = self.client._load_query("set_ticket.sql")
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    *args
                )

            self.message = inter.message
            await _disable_all_items(self)

            await ticket.send(
                content=f"Opened by {inter.user.mention}",
                view=PersistentViews.TicketClose(
                    self.client
                )
            )


        async def interaction_check(
                self, 
                interaction: Interaction
        ) -> bool:
            
            await interaction.response.defer()

            query = """
            SELECT * 
            FROM tickets
            WHERE channel_id = $1
            AND is_open = FALSE;
            """
            
            async with self.pool.acquire() as conn:
                results = await conn.fetch(
                    query,
                    interaction.channel_id
                )

            if not interaction.channel.permissions_for(interaction.guild.me).manage_channels:

                await interaction.followup.send(
                    content="I don't have permisson to do that.",
                    ephemeral=True
                )


            if not results:
                await interaction.edit_original_response(
                    view=None,
                    content="This ticket is not closed"
                )

                return False
            

            return True
    
        async def on_error(
                self, 
                interaction: Interaction, 
                error: Exception, 
                item: Item[Any]
        ) -> None:
            
            if isinstance(error, CustomOnCooldownException):

                embed = ErrorEmbed(
                    error.text
                )


            await (
                interaction.response.send_message 
                if not interaction.response.is_done() 
                else interaction.followup.send
            )(
                embed=embed,
                ephemeral=True
            )


    def add_views(
            self
    ) -> None:
        
        for view in self.views:
            self.client.add_view(view=view(client=self.client))
    
    @property
    def views(self):
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, type) and issubclass(attr, _View):
                yield attr
