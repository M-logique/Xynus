from datetime import datetime as _datetime
from typing import Any as _Any

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