from datetime import datetime as _datetime
from typing import Any as _Any
from typing import Sequence as _Sequence
from typing import Union as _Union

from discord import Color as _Color
from discord import Embed as _Embed
from discord import Member as _Member

from discord.ext import commands as _commands

from bot.core.settings import settings

_color = _Color.from_rgb(*settings.MAIN_COLOR)


class SimpleEmbed(_Embed):

    def __init__(
            self,
            client: _commands.Bot,
            **kwrgs
    ):
        super().__init__(
            color=_color,
            timestamp=_datetime.now(),
            **kwrgs
        )

        self.set_footer(
            text=client.user.name,
            icon_url=client.user.avatar
        )

class ErrorEmbed(_Embed):


    def __init__(self, error: str,
                *args: _Any, 
                **kwgrs: _Any) -> None:


        super().__init__(title="We Got an Error!",
                        color=_Color.from_rgb(255, 3, 7),
                        description="⚠️ {}".format(error),
                        timestamp=_datetime.now(),
                        *args, 
                        **kwgrs
                    )
        
class CommandsEmbed(_Embed):

    def __init__(
            self,
            commands: _Sequence[_commands.Command],
            title: str,
            **kwrgs
    ):
        
        base = "```diff\n+ {}\n```\n**Commands**: {}\n".format(
            title,
            len(commands)
        )

        for command in commands:
            
            text_to_add = "\n__**{}{}**__: *`{}`*".format(
                f"{command.parent} " if command.parent else "",
                command.name,
                command.description if command.description else "No description yet!"
            )

            base+=text_to_add
            

        super().__init__(
            timestamp=_datetime.now(),
            color=_color,
            description=base,
            **kwrgs
        )

class DynamicHelpEmbed(SimpleEmbed):

    def __init__(
            self,
            client: _commands.Bot,
            ctx: _commands.Context,
            prefix: _Union[_Sequence, str],
            commands_that_user_can_use: _Sequence[_commands.Command],
            commands: _Sequence[_commands.Command],
            **kwrgs
    ):
        

        prefix = [*filter(lambda x: "@" not in x, prefix)]

        self.single_prefix = prefix if isinstance(prefix, str) else prefix[0]
        prefix = prefix if isinstance(prefix, str) else f'[{", ".join(prefix)}]'

        
        
        description = (
            f"・ Prefix: `{prefix}`\n"
            f"・ Total commands: `{len(commands)}` | Usable by you (here): {len(commands_that_user_can_use)}\n"
            f"・ Type `{self.single_prefix}help <command | module>` for more info\n"
        )

    
        super().__init__(
            client=client,
            description=description,
            **kwrgs
        )


        self.set_thumbnail(
            url=client.user.display_avatar
        )

        self.set_footer(
            icon_url=ctx.author.display_avatar,
            text="Invoked by {}".format(
                ctx.author.display_name
            )
        )