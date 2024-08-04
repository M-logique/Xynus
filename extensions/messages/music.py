from discord import app_commands, VoiceClient
from discord.ext import commands
from wavelink import Node, Pool, Search, Playable, Player, NodeReadyEventPayload, TrackStartEventPayload, TrackEndEventPayload

from typing import Union, Optional, List
from bot.core import Client, guilds
from bot.templates.cogs import Cog
from bot.templates.wrappers import check_voice_client

LAVALINKS = [
    # {
    #     "identifier": "Akshtt - v4 Free",
    #     "password": "admin",
    #     "host": "lava.akshat.tech",
    #     "port": 443,
    #     "secure": True
    # },
    # {
    #     "identifier": "Creavite US1 Lavalink",
    #     "password": "auto.creavite.co",
    #     "host": "us1.lavalink.creavite.co",
    #     "port": 20080,
    #     "secure": False
    # }

    {
        "identifier": "Lavat Link",
        "password": "youshallnotpass",
        "host": "dv-n1.divahost.net",
        "port": 50664,
        "secure": False
    },

]


class Music(Cog):
    def __init__(self, client: Client) -> None:
        self.emoji = None
        super().__init__(client)

    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(
        self,
        node: NodeReadyEventPayload
    ):
        self.client.logger.info(f"Node {node.node.identifier} is ready")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload) -> None:
        self.client.logger.info(f"Started playing {payload.track.title}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload) -> None:
        self.client.logger.info(f"Finished playing {payload.track.title}")



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
        tracks: Search = await Playable.search(query)


        if not tracks:
            return await ctx.reply("Hmm didn't find smth")

        track = tracks[0]

        await self._add_track(
            player=player,
            items=track
        )

        await ctx.reply(f"Started playing {track.title}")

        


    async def _add_track(
            self,
            player: Union[Player, VoiceClient],
            items: Union[List[Playable], Playable]
    ):
        

        if not isinstance(items, List):
            items = [items]


        async def queue_items(
                remove_first_one: Optional[bool] = False
        ):
            if remove_first_one:
                items.remove(items[0])
            
            await player.queue.put_wait(items)

        if not isinstance(player, VoiceClient):
            if player.playing or player.paused:
                return await queue_items()


        await player.play(items[0])
        return await queue_items(remove_first_one=True)



async def setup(c: Client):
    nodes = [
        Node(
            identifier=i.get("identifier"),
            password=i.get("password"),
            uri="{}://{}:{}".format(
                "https" if i.get("scure") else "http",
                i.get("host"),
                i.get("port")
            ),
            
        )
        
        for i in LAVALINKS
    ]
    await Pool.connect(nodes=nodes, client=c, cache_capacity=100)
    await c.add_cog(Music(c))