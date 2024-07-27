from datetime import datetime as _datetime
from typing import Any as _Any
from typing import Sequence as _Sequence

from discord import Color as _Color
from discord import Embed as _Embed
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