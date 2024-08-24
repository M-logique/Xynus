from typing import TYPE_CHECKING, Any, Optional, Self, Union

from discord import PartialEmoji
from discord.ext import commands as _commands

from ..core import Xynus as _Xynus

if TYPE_CHECKING:
    from ..core import Xynus

from discord.ui import Modal


class XynusCog(_commands.Cog):

    if TYPE_CHECKING:
        emoji: str


    def __init__(self, client: _Xynus) -> None:
        self.client: "Xynus" = client


    def __init_subclass__(cls, *, emoji: Optional[Union[str, PartialEmoji]] = None):
        
        # Since I'm organizing commands based on Cogs,
        # I need an emoji for the SelectOption in the HelpSelect,
        # which will be defined here.

        cls.emoji = emoji