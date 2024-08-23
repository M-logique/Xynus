from typing import TYPE_CHECKING, Optional

from discord import PartialEmoji
from discord.ext import commands as _commands

from ..core import Xynus as _Xynus

if TYPE_CHECKING:
    from ..core import Xynus

class XynusCog(_commands.Cog):

    def __init__(self, client: _Xynus) -> None:
        self.client: "Xynus" = client
        self.emoji: Optional[PartialEmoji] = None 
        
        # Since I'm organizing commands based on Cogs,
        # I need an emoji for the SelectOption in the HelpSelect,
        # which will be defined here.