from typing import TYPE_CHECKING, Annotated, List

from discord import Color
from discord.ext import commands

from ..utils.functions import strip_codeblock, verify_link

if TYPE_CHECKING:
    from .context import XynusContext



class EmbedFieldFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    name: str
    value: str
    inline: bool = True


class EmbedFooterFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    text: str
    icon: Annotated[str, verify_link] | None = None


class EmbedAuthorFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    name: str
    icon: Annotated[str, verify_link] | None = None
    url: Annotated[str, verify_link] | None = None


class EmbedFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    title: str | None = None
    description: str | None = None
    color: Color | None = None
    field: List[EmbedFieldFlags] = commands.flag(converter=list[EmbedFieldFlags], default=None)
    footer: EmbedFooterFlags | None = None
    image: Annotated[str, verify_link] | None = None
    author: EmbedAuthorFlags | None = None
    thumbnail: Annotated[str, verify_link] | None = None

    @classmethod
    async def convert(cls, ctx: "XynusContext", argument: str):  # pyright: ignore[reportIncompatibleMethodOverride]
        argument = strip_codeblock(argument).replace(' —', ' --')
        # Here we strip the code block if any and replace the iOS dash with
        # a regular double-dash for ease of use.
        return await super().convert(ctx, argument)
    



class JsonFlag(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    json: str


