from typing import TYPE_CHECKING, Optional, Union, Tuple

from discord import PartialEmoji
from discord.ext import commands as _commands


if TYPE_CHECKING:
    from ..core import Xynus


class XynusCog(_commands.Cog):
    """
    Base class for Cogs in the Xynus bot. Handles initialization and subclass customization, 
    including assigning an emoji to the Cog for use in help menus.
    """

    if TYPE_CHECKING:
        emoji: Optional[Union[str, PartialEmoji]] = None

    __slots__: Tuple[str, ...] = (
        "client",
        "emoji"
    )

    def __init__(self, client: "Xynus") -> None:
        """
        Initializes the Cog with a reference to the bot client.

        :param client: The bot client instance.
        :type client: :class:`Xynus`
        """
        self.client: "Xynus" = client


    def __init_subclass__(cls, *, emoji: Optional[Union[str, PartialEmoji]] = None):
        """
        Initializes subclasses of XynusCog, assigning an emoji for use in help menus.

        :param emoji: The emoji to represent the Cog in the help menu. Can be a string or PartialEmoji.
        :type emoji: Optional[Union[str, PartialEmoji]]
        """
        
        # Since I'm organizing commands based on Cogs,
        # I need an emoji for the SelectOption in the HelpSelect,
        # which will be defined here.

        cls.emoji = emoji
        