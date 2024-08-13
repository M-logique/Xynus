from functools import wraps
from types import FunctionType
from typing import Union

from discord.ext import commands

from ..utils.functions import disable_all_items


def check_views(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        from bot.core import Client

        ctx: commands.Context = args[1]
        client: Client = args[0].client
        user_id = ctx.author.id

        prev_view = client.view_cache.get(user_id)

        if prev_view:
            await disable_all_items(prev_view)
            del client.view_cache[user_id]

        
        return await coro(*args, **kwargs)
        
    
    return wrapper


def check_views_interaction(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        

        interaction = args[1]
        client = args[0].client
        user_id = interaction.user.id

        prev_view = client.view_cache.get(user_id)

        if prev_view:
            await disable_all_items(prev_view)
            del client.view_cache[user_id]

        
        return await coro(*args, **kwargs)
        
    
    return wrapper

def check_voice_client(
        coro: FunctionType
): 
    @wraps(coro)
    async def wrapper(*args, **kwrgs):
        from wavelink import Player


        ctx: commands.Context = args[1]

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
    @wraps(coro)
    async def wrapper(*args, **kwrgs):
        from wavelink import Player


        ctx: commands.Context = args[1]

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