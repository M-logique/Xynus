from functools import wraps
from types import FunctionType
from typing import Union

from discord import Interaction
from discord.ext.commands import Context, CooldownMapping
from discord.ext.commands.cooldowns import BucketType
from .exceptions import CustomOnCooldownException

class CooldownMapingCache:

    ticket_edit_cooldown = CooldownMapping.from_cooldown(
        2,
        10 * 60, # 10 minutes
        BucketType.channel.get_key
    )




def ticket_edit_cooldown(
        coro: FunctionType
):
    
    @wraps(coro)
    async def wrapper(*args, **kwrgs):
        
        inter_or_ctx: Union[Interaction, Context] = args[1]

        retry_after = CooldownMapingCache.ticket_edit_cooldown.update_rate_limit(inter_or_ctx)

        if retry_after:

            raise CustomOnCooldownException(
                cooldown= 10 * 60,
                retry_after=retry_after,
                type=BucketType.channel
            )


        return await coro(*args, **kwrgs)

    

    return wrapper