from functools import wraps
from types import FunctionType
from typing import TYPE_CHECKING, Union

from discord import Forbidden, HTTPException

if TYPE_CHECKING:
    from discord import Interaction

    from ..core import Xynus
    from .context import XynusContext



def check_views(
        coro: FunctionType
):
    """
    Decorator to disable previous active view items.
    """
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        

        ctx: "XynusContext" = args[1]
        client: "Xynus" = args[0].client
        user_id = ctx.author.id

        prev_view = client.views.get(user_id)

        if prev_view:
            if hasattr(prev_view, "message"):
                try:
                    await prev_view.message.edit(view=None)
                except (Forbidden, HTTPException, AttributeError):
                    pass
            del client.views[user_id]

        
        return await coro(*args, **kwargs)
        
    
    return wrapper


def check_views_interaction(
        coro: FunctionType
):
    """
    Decorator to disable previous active view items.
    """
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        

        interaction: "Interaction" = args[1]
        client: "Xynus" = args[0].client
        user_id = interaction.user.id

        prev_view = client.views.get(user_id)

        if prev_view:
            if hasattr(prev_view, "message"):
                try:
                    await prev_view.message.edit(view=None)
                except (Forbidden, HTTPException, AttributeError):
                    pass
            del client.views[user_id]

        
        return await coro(*args, **kwargs)
        
    
    return wrapper

def check_voice_client(
        coro: FunctionType
): 
    """
    Decorator to check guild voice clients.
    """
    @wraps(coro)
    async def wrapper(*args, **kwrgs):
        from wavelink import Player

        ctx: "XynusContext" = args[1]

        await ctx.defer()

        author_voice = ctx.author.voice
        vc_client: Union[Player, None] = ctx.guild.voice_client

        if not author_voice or not author_voice.channel:
            return await ctx.reply("You need to join a voice channel first.")
        
        

        if not vc_client:
            vc_client = await author_voice.channel.connect(cls=Player)
        
        if  len(vc_client.channel.members) == 1:

            await vc_client.disconnect()
            await author_voice.channel.connect(cls=Player)


        if not hasattr(vc_client, "home"):
            vc_client.home = ctx.channel
            
        elif vc_client.home != ctx.channel:
            vc_client.home = ctx.channel
        
        if vc_client and vc_client.channel.id != author_voice.channel.id:
            return await ctx.reply(f"You need to join <#{vc_client.channel.id}>")
        



        return await coro(*args, **kwrgs)
    
    return wrapper


def check_for_player(
        coro: FunctionType
): 
    """
    Decorator to check if there is an active player in ctx.guild or no.
    """
    @wraps(coro)
    async def wrapper(*args, **kwrgs):
        from wavelink import Player

        ctx: "XynusContext" = args[1]

        await ctx.defer()

        author_voice = ctx.author.voice

        player: Union[Player, None] = ctx.voice_client
        

        if not player:
            return await ctx.reply("Didn't find any player here.")

        if not author_voice or not author_voice.channel:
            return await ctx.reply("You need to join a voice channel first.")
        
        if  len(player.channel.members) == 1:

            await player.disconnect()
            await author_voice.channel.connect(cls=Player)

            
        if player and player.channel.id != author_voice.channel.id:
            return await ctx.reply(f"You need to join <#{player.channel.id}>")
        


        return await coro(*args, **kwrgs)
    
    return wrapper
