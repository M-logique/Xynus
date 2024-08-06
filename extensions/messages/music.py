from typing import List, Optional, Union, Any

from discord import VoiceClient, app_commands, Member
from discord.ext import commands
from wavelink import (Node, NodeReadyEventPayload, Playable, Player, TrackSource, Playlist,
                      Pool, Search, TrackEndEventPayload,
                      TrackStartEventPayload)

from bot.core import Client, guilds
from bot.templates.cogs import Cog
from bot.templates.wrappers import check_voice_client, check_for_player
from bot.utils.config import Emojis
from bot.templates.embeds import SimpleEmbed


emojis = Emojis()
_seek, _play, _note = emojis.get("end"), emojis.get("next"), emojis.get("music_note")




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
        
        embed = self._gen_embed(
            description=f"{_note} Started playing [`{payload.track.title}`]({payload.track.uri or 'https://github.com/M-logique/TTK-2'})`"
        )

        await payload.player.home.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload) -> None:
        if not hasattr(payload.player, "home"):
            return    
        

        cached_value = self.client.db._traverse_dict(
            self.cache,
            [payload.player.guild.id, "queue"],
            create_missing=True
        )
        if cached_value.get("queue"):
            self.cache[payload.player.guild.id]["queue"].pop(0)
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

        player.queue._items

        # await ctx.reply(f"[**{track.title}**]({track.uri or 'https://github.com/M-logique/TTK-2'}) queued - {length}")
        

    @commands.hybrid_command(
            name="stop", 
            aliases=["clearqueue"]
    )
    @app_commands.guilds(*guilds)
    @check_for_player
    async def stop(
        self,
        ctx: commands.Context
    ):
        
        player: Union[Player, None] = ctx.voice_client
        
        player.queue.clear()
        del self.cache[ctx.guild.id]["queue"]

        await player.skip(force=True)
        
        


    async def _add_track(
            self,
            player: Union[Player, VoiceClient],
            items: Union[List[Playable], Playable],
            ctx: commands.Context
    ):
        
        queue = self._get_cache(
            ctx.guild.id,
            "queue"
        )

        if not queue:
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

    def _gen_embed(
            self,
            description: str,
            author: Optional[Member] = None,
    ) -> SimpleEmbed:
        embed = SimpleEmbed(
            self.client,
            description=description
        )

        if author:
            embed.set_footer(
                text=f"Invoked by {author.display_name}",
                icon_url=author.display_avatar
            )
        else:
            embed._footer = {}

        return embed

    def _get_cache(
            self,
            guild_id: int,
            value: str
    ) -> Union[None, Any]:

        value: dict = self.client.db._traverse_dict(
            self.cache,
            [guild_id, value],
            create_missing=True
        )

        return value.get(value)

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
