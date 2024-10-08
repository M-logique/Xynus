from datetime import datetime as _datetime
from typing import TYPE_CHECKING
from typing import Optional as _Optional
from typing import Sequence as _Sequence
from typing import Union as _Union

from discord import Color as _Color
from discord import Embed as _Embed
from discord import Interaction as _Interaction
from discord.ext import commands as _commands

from ..utils.functions import format_command_params, split_camel_case

if TYPE_CHECKING:
    from .context import XynusContext


class SimpleEmbed(_Embed):
    """
    Discord embed with a timestamp and an optional footer including client's name and avatar.
    """
    def __init__(
            self,
            client: _Optional[_commands.Bot] = None,
            **kwargs
    ):
        
        from ..core import _settings



        super().__init__(
            timestamp=_datetime.now(),
            color=_Color.from_rgb(*_settings.MAIN_COLOR),
            **kwargs
        )

        if client:
            self.set_footer(
                text=client.user.name,
                icon_url=client.user.avatar
            )

class ErrorEmbed(_Embed):


    def __init__(
        self, 
        error: str,
        /
    ) -> None:


        super().__init__(
            description=f":x: **{error}**",
            color=_Color.from_rgb(255, 3, 7)
        )
        
class CommandsEmbed(_Embed):

    def __init__(
            self,
            commands: _Sequence[_commands.Command],
            title: str,
            prefix: str,
            total_commands: int,
            **kwrgs
    ):
        from ..core import _settings
        base = "```diff\n+ {}\n```\n**Commands**: {}\n".format(
            title,
            total_commands
        )

        for command in commands:
            
            text_to_add = "\n__**{}{}**__: *`{}`*".format(
                prefix,
                command.qualified_name,
                command.description if command.description else "No description yet!"
            )

            base+=text_to_add
            

        super().__init__(
            timestamp=_datetime.now(),
            description=base,
            color=_Color.from_rgb(*_settings.MAIN_COLOR),
            **kwrgs
        )

class DynamicHelpEmbed(SimpleEmbed):

    def __init__(
            self,
            client: _commands.Bot,
            prefix: _Union[_Sequence, str],
            commands: _Sequence[_commands.Command],
            ctx: _Optional[_commands.Context] = None,
            interaction: _Optional[_Interaction] = None,
            **kwrgs
    ):
        

        if interaction:
            user = interaction.user
        elif ctx:
            user = ctx.author

        self.single_prefix = prefix[0]
        prefix = f'[{", ".join(prefix)}]'

        
        
        description = (
            f"・ Prefix: `{prefix}`\n"
            f"・ Total commands: {len(commands)}\n"
            f"・ Type `{self.single_prefix}help <command | module>` for more info\n"
            f"> ***Choose a category to view its commands***"
        )

    
        super().__init__(
            description=description,
            **kwrgs
        )


        self.set_thumbnail(
            url=client.user.display_avatar
        )

        self.set_footer(
            icon_url=user.display_avatar,
            text="Invoked by {}".format(
                user.display_name
            )
        )

class CommandInfoEmbed(SimpleEmbed):

    def __init__(
            self, 
            client: _commands.Bot, 
            command: _commands.Command,
            full_name: str,
            **kwrgs
    ):

        description = (
            "```diff\n- [] = optional argument\n- \u003c\u003e = required argument\n- Do NOT type these when using commands!\n```"
            f"\n> {command.description if command.description else 'No description yet'}"
        )

        title = split_camel_case(command.cog_name)

        self.add_field(
            name="Aliases",
            inline=False,
            value=" | ".join([f"`{alias}`" for alias in command.aliases]) if command.aliases else "`No aliases yet`"
        )


        if command.usage:
            self.add_field(
                name="Usage",
                value=f"```\n{command.usage}\n```",
                inline=False
            )


        self.add_field(
            name="Syntax",
            value=f"`{full_name} {format_command_params(command)}`",
            inline=False
        )


        self.set_author(
            icon_url=client.user.avatar,
            name=title
        )

        super().__init__(
            description = description,
            client=client,
            **kwrgs
        )


class ConfirmationEmbed(_Embed):

    def __init__(
            self,
            text: str,
            timeout: int,
            /
    ):
        super().__init__(
            description=text,
        )

        self.set_footer(
            text=(
                f'Click on either "Yes" or "No" to confirm. You have {timeout} second'
                's' if timeout > 1 else ''
            )
        )

class MappingInfoEmbed(_Embed):
    
    def __init__(
            self,
            ctx: "XynusContext",
            trigger: str,
            command: str,
            created_at: int
    ):
        
        super().__init__(
            title=f"Mapping: {trigger.capitalize()}",
            description=(
                f"🔰 **Author**: {ctx.user.mention}\n"
                f"❔ **Trigger**: `{trigger}`\n"
                f"⌚️ **Created at**: <t:{created_at}:F>"
            ),
            color=ctx.client.color
        )
        self.add_field(
            inline=False,
            name="🧪 Command:",
            value=f"```\n{command}\n```"[:1024:]
        )
        self.set_footer(
            text=f"Invoked by {ctx.user.display_name}",
            icon_url=ctx.user.display_avatar
        )