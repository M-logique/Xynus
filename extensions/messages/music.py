from typing import List, Optional, Union, cast

from discord import VoiceClient, app_commands
from discord.ext import commands
from wavelink import (Node, NodeReadyEventPayload, Playable, Player, TrackSource, Playlist,
                      Pool, Search, TrackEndEventPayload,
                      TrackStartEventPayload)

from bot.core import Client, guilds
from bot.templates.cogs import Cog
from bot.templates.wrappers import check_voice_client
from bot.utils.config import Emojis


emojis = Emojis()
_seek, _play = emojis.get("end"), emojis.get("next")




LAVALINKS = [
    # {
    #     "identifier": "Akshtt - v4 Free",
    #     "password": "admin",
    #     "host": "lava.akshat.tech",
    #     "port": 443,
    #     "secure": True
    # },
    {
        "identifier": "Creavite US1 Lavalink",
        "password": "auto.creavite.co",
        "host": "us1.lavalink.creavite.co",
        "port": 20080,
        "secure": False
    },
    # {
    #     "identifier": "Lavat Link",
    #     "password": "youshallnotpass",
    #     "host": "dv-n1.divahost.net",
    #     "port": 50664,
    #     "secure": False
    # },



]


class Music(Cog):
    def __init__(self, client: Client) -> None:
        self.emoji = emojis.get("music_note")
        self.cache = {}
        super().__init__(client)

    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(
        self,
        node: NodeReadyEventPayload
    ):
        self.client.logger.info(f"Node {node.node.identifier} is ready")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload) -> None:
        if not hasattr(payload.player, "home"):
            return
        
        await payload.player.home.send(f"Started playing {payload.track.title}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload) -> None:
        if not hasattr(payload.player, "home"):
            return    

        await payload.player.home.send(f"Finished playing {payload.track.title}")



    @commands.hybrid_command(
        name="play",
        aliases=["p"]
    )
    @commands.guild_only()
    @app_commands.guilds(*guilds)
    @check_voice_client
    async def play(
        self,
        ctx: commands.Context,
        *,
        query: str
    ):
        
        
        player: Player = ctx.guild.voice_client
        tracks: Search = await Playable.search(query, source=TrackSource.SoundCloud)


        if not tracks:
            return await ctx.reply("Hmm didn't find anything.")

        if isinstance(tracks, Playlist):
            track = tracks
        else:
            track = tracks[0]

        await self._add_track(
            player=player,
            items=track,
            ctx=ctx
        )


        length = self._milliseconds_to_minutes_seconds(track.length)

        await ctx.reply(f"[**{track.title}**]({track.uri or 'https://github.com/M-logique/TTK-2'}) queued - {length}")
        

    @commands.hybrid_command(
            name="stop", 
            aliases=["clearqueue"]
    )
    @app_commands.guilds(*guilds)
    async def stop(
        self,
        ctx: commands.Context
    ):
        
        player: Union[Player, None] = ctx.voice_client
        

        if not player:
            return await ctx.reply("Didn't find any player here.")
        
        
        player.queue.clear()
        await player.skip(force=True)

        


    async def _add_track(
            self,
            player: Union[Player, VoiceClient],
            items: Union[List[Playable], Playable],
            ctx: commands.Context
    ):
        
        queue = self.client.db._traverse_dict(
            self.cache,
            [ctx.guild.id, "queue"],
            create_missing=True
        )

        if queue == {}:
            self.cache[ctx.guild.id]["queue"] = []


        value = {
            "by": ctx.author
        }

        
        if not isinstance(items, List):
            items = [items]


        async def queue_items(
                remove_first_one: Optional[bool] = False
        ):
            if remove_first_one:
                items.remove(items[0])
            for item in items:
                
                new_value = value
                new_value["track"] = item
                self.cache[ctx.guild.id]["queue"].append(new_value)

            await player.queue.put_wait(items)

        if not isinstance(player, VoiceClient):
            if player.playing or player.paused:
                return await queue_items()

        
        await player.play(items[0])
        return await queue_items(remove_first_one=True)

    def _milliseconds_to_minutes_seconds(
            self,
            ms: int
    ):
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"


async def setup(c: Client):
    nodes = [
        Node(
            identifier=i.get("identifier"),
            password=i.get("password"),
            uri="{}://{}:{}".format(
                "https" if i.get("secure") else "http",
                i.get("host"),
                i.get("port")
            ),
            
        )
        
        for i in LAVALINKS
    ]

    await Pool.connect(nodes=nodes, client=c, cache_capacity=100)
    await c.add_cog(Music(c))
