from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Tuple, TypedDict

from discord import app_commands
from discord.errors import ClientException
from discord.ext import commands
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands.cooldowns import BucketType, Cooldown


class XynusException(ClientException):

    __slots__: Tuple[str, ...] = ()


class XynusTracebackOptional(TypedDict, total=False):
    author: int
    guild: Optional[int]
    channel: int
    command: Optional[commands.Command[Any, ..., Any] | app_commands.Command[Any, ..., Any] | app_commands.ContextMenu]


class XynusTraceback(XynusTracebackOptional):
    time: datetime
    exception: Exception



class CustomOnCooldownException(CommandOnCooldown):

    def __init__(
            self, 
            cooldown: Cooldown, 
            retry_after: float, 
            type: BucketType
    ) -> None:
        
        self.text = (
            "Due to prevent discord rate limits, this action is on cooldown. You can retry after "
            f"{round(retry_after, 3)} second{'' if retry_after < 2 else 's'}"
        )

        super().__init__(cooldown, retry_after, type)


class InvalidModalField(Exception): ...
