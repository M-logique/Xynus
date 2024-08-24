from logging import getLogger
from typing import Any, Dict, List, Optional, Union

from discord import Member, Message, VoiceClient, app_commands
from discord.ext import commands
from wavelink import (Node, NodeReadyEventPayload, Playable, Player, Playlist,
                      Pool, Search, TrackEndEventPayload, TrackSource,
                      TrackStartEventPayload)

from bot.templates.buttons import DeleteButton
from bot.templates.cogs import XynusCog
from bot.templates.embeds import SimpleEmbed
from bot.templates.views import Pagination
from bot.templates.wrappers import check_for_player, check_voice_client
from bot.utils.config import Emojis
from bot.utils.functions import chunker

emojis = Emojis()
note = emojis.get("music_note")
checkmark = emojis.get("checkmark")
crossmark = emojis.get("crossmark")


#TODO: Make the bot pause the player when everyone left player's channel.


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


class Music(XynusCog, emoji=emojis.get("music_note")):

    log = getLogger("xynus.music")
    cache = dict()

    # Listeners
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(
        self,
        node: NodeReadyEventPayload
    ):
        self.log.info(f"Node {node.node.identifier} is ready")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload) -> None:
        queue = self._get_cache(
            payload.player.guild.id,
            "queue"
        )
        
        
        if not hasattr(payload.player, "home") or not queue:
            return
        
        

        length = self._milliseconds_to_time(payload.track.length)

        kwrgs = {
            "description": (
                f"{note} **Started playing** [`{payload.track.title}`]({payload.track.uri or 'https://github.com/M-logique/TTK-2'}) - [`{length}`]\n"
                f"**Author**: `{payload.track.author}`"
            )
        }


        if queue:
            kwrgs["author"] = queue[0]["by"]
        

        embed = self._gen_embed(**kwrgs)


        await payload.player.home.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload) -> None:
        if not hasattr(payload.player, "home"):
            return    
        

        cached_value = self._get_cache(
            payload.player.guild.id,
            "queue"
        )

        ignore_stopped_message = self._get_cache(
            payload.player.guild.id, 
            "ignore_stopped_message"
        )


        if cached_value:
            await payload.player.play(cached_value[0].get("track"))
            self.cache[payload.player.guild.id]["queue"].pop(0)
        
        elif not payload.player.queue:

            del self.cache[payload.player.guild.id]

            if not ignore_stopped_message:
                await payload.player.home.send("Stopped the player as the queue is empty.")

            await payload.player.disconnect()

    # Commands



    @commands.hybrid_command(
            name="join",
            description="Make the bot join your current voice channel.",
            aliases=["connect", "j"]
    )
    @app_commands.guild_only()
    @check_voice_client
    async def join(
        self,
        ctx: commands.Context
    ):
        
        return await self._reply(ctx, f"Joined to {ctx.author.voice.channel}.")

    @commands.hybrid_command(
            name="leave",
            description="Clears the queue and leaves the voice channel.",
            aliases=["disconnect", "dc"]
    )
    @app_commands.guild_only()
    @check_for_player
    async def leave(
        self,
        ctx: commands.Context
    ):
        player: Union[Player, None] = ctx.guild.voice_client
        await player.disconnect()

        return await self._reply(ctx, f"Disconnected from {ctx.author.voice.channel}.")
    

    @commands.hybrid_command(
        name="play",
        aliases=["p"],
        description="Playing a track or playlist by providing a link or search query."
    )
    @commands.guild_only()
    @app_commands.describe(
        query = "Provide a name or url to find and play track(s)."
    )
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
            return await ctx.reply("didn't find anything.")

        if isinstance(tracks, Playlist):
            track = tracks
        else:
            track = tracks[0]

        await self._add_track(
            player=player,
            items=track,
            ctx=ctx
        )


        length = self._milliseconds_to_time(track.length)

        queue = self._get_cache(
            ctx.guild.id,
            "queue"
        )

        if not queue:
            embed = self._gen_embed(
                author=ctx.author,
                description=(
                    f"{note} **Started playing** [`{track.title}`]({track.uri or 'https://github.com/M-logique/TTK-2'}) - [`{length}`]\n"
                    f"**Author**: `{track.author}`"
                ),
            )
        else:

            embed = self._gen_embed(
                author=ctx.author,
                description=f"[**{track.title}**]({track.uri or 'https://github.com/M-logique/TTK-2'}) [`{length}`] **queued at position `#{len(queue)}`**"
            )

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)


        await ctx.reply(embed=embed)
        

    @commands.hybrid_command(
            name="stop", 
            aliases=["clearqueue"],
            description="Stop and clear the queue."
    )
    @app_commands.guild_only()
    @check_for_player
    async def stop(
        self,
        ctx: commands.Context
    ):
        
        player: Union[Player, None] = ctx.voice_client

        player.queue.clear()
        del self.cache[ctx.guild.id]["queue"]

        ignore_stopped_message = self._get_cache(
            ctx.guild.id, 
            "ignore_stopped_message"
        )

        if not ignore_stopped_message:
            self.cache[ctx.guild.id]["ignore_stopped_message"] = True

        await player.skip(force=True)


        await self._reply(ctx, f"{checkmark} Stopped the player.")
        
    @commands.hybrid_command(
            name="skip", 
            aliases=["sk"],
            description="Skip the current playing song."
    )
    @check_for_player
    async def skip(
        self,
        ctx: commands.Context
    ):



        player: Union[Player, None] = ctx.voice_client

        await player.skip(force=False)
        
        queue = self._get_cache(
            ctx.guild.id,
            "queue"
        )

        if not queue:
            return 
        
        track: Playable = queue[0]["track"]
        track_author: Member = queue[0]["by"]

        track_length = self._milliseconds_to_time(track.length)

        await self._reply(ctx, f"{checkmark} Skipped to [`{track.title}`]({track.uri}) - [`{track_length}]`. (Added by {track_author.mention})")

    
    @commands.hybrid_command(
            name="volume", 
            aliases=["v"],
            description="Change the volume of currently playing music."
    )
    @app_commands.describe(
        number = "Provide a volume number."
    )
    @app_commands.guild_only()
    @check_for_player
    async def volume(
        self,
        ctx: commands.Context,
        number: int
    ):
        if number < 0 or number > 1000:
            return await self._reply(ctx, "Enter a number between 0-1000")
        
        player: Union[Player, None] = ctx.voice_client

        await player.set_volume(number)


        await self._reply(ctx, f"{checkmark} Now the player volume is `{number}`")



    @commands.hybrid_command(
            name="pause",
            description="Pause the currently playing music."
    )
    @app_commands.guild_only()
    @check_for_player
    async def pause(
        self,
        ctx: commands.Context,
    ):
        
        player: Union[Player, None] = ctx.voice_client
        if not player.paused:
            await player.pause(True)
            return await self._reply(ctx, f"{checkmark} Paused the player.")
        
        await self._reply(ctx, f"{crossmark} Player is already paused.")
    
    @commands.hybrid_command(
            name="resume",
            aliases=["r"],
            description="Resume the currently playing music."
    )
    @check_for_player
    async def resume(
        self,
        ctx: commands.Context,
    ):
        
        player: Union[Player, None] = ctx.voice_client
        if player.paused:
            await player.pause(False)
            return await self._reply(ctx, f"{checkmark} Resumed the player.")
        


        await self._reply(ctx, f"{crossmark} Player is not paused.")

    @commands.hybrid_command(
            name="seek",
            description="Set the position of the playing track."
    )
    @app_commands.describe(
        time = "Length of time. Example: 1:30"
    )
    @check_for_player
    async def seek(
        self,
        ctx: commands.Context,
        time: str
    ):
        
        player: Union[Player, None] = ctx.voice_client

        try:
            total_ms = self._time_to_milliseconds(time)
        except:
            return await ctx.reply("Time must be formatted as `mm:ss` or `hh:mm:ss`")


        if total_ms > player.current.length:
            total_ms = player.current.length

        await player.seek(total_ms)

        await self._reply(ctx, f"Seeking `{player.current.title}` to {self._milliseconds_to_time(total_ms)}.")

    @commands.hybrid_command(
            name="remove",
            description="Remove the specified track from the queue.",
            aliases=["rm"]
    )
    @app_commands.describe(
        position = "The song's position in the queue."
    )
    @app_commands.guild_only()
    @check_for_player
    async def remove(
        self,
        ctx: commands.Context,
        position: int
    ):
        
        queue = self._get_cache(
            ctx.guild.id,
            "queue"
        )

        if not queue:
            return await ctx.reply("Didn't remove the song as the queue is empty.")


        if position < 1 or position > len(queue):
            return await ctx.reply("Provide a valid position please.")
        

        
        track = queue[position-1]
        self.cache[ctx.guild.id]["queue"].pop(position-1)

        await self._reply(ctx, f"{checkmark} Removed the song `{track.title}` from the queue.")
        


    @commands.hybrid_command(
            name="nowplaying",
            aliases=["np"], 
            description="Show the currently playing song."
    )
    @app_commands.guild_only()
    @check_for_player
    async def nowplaying(
        self,
        ctx: commands.Context,
    ):
        
        player: Union[Player, None] = ctx.voice_client
        current = player.current
        length = self._milliseconds_to_time(current.length)
        progress_bar = self._show_progress(player.position, current.length)


        embed = self._gen_embed(
            description=(
                f"[**{current.title}**]({current.uri or 'https://github.com/M-logique/TTK-2'}) [`{length}`]\n"
                f"**Author**: `{current.author}`\n\n"
                f"{progress_bar}"
            ),
            author=ctx.author
        )

        if current.artwork:
            embed.set_thumbnail(url=current.artwork)


        await ctx.reply(
            embed=embed
        )

    @commands.hybrid_command(
            name="queue",
            aliases=["q"],
            description="Display a list of current songs in the queue."
    )
    @check_for_player
    async def queue(
        self,
        ctx: commands.Context,
    ):
        
        queue = self._get_cache(
            ctx.guild.id,
            "queue"
        )

        if not queue:
            return await self._reply(ctx, f"{crossmark} There is not any track in the queue.")

        async def get_page(
                index: int
        ):
            
            chunks = chunker(queue, 10)

            txt = ""
            track_index = index * 10

            for value in chunks[index]:
                
                track_index+=1

                track = value.get("track")
                track_author = value.get("by")

                length = self._milliseconds_to_time(track.length)

                txt+=f"[`{track_index}`] [**{track.title}**]({track.uri or 'https://github.com/M-logique/TTK-2'}) [`{length}`] - {track_author.mention}\n"


            embed = self._gen_embed(
                description=txt
            )

            kwrgs = {
                "embed": embed
            }

            return kwrgs, len(chunks)
        
        pagination_view = Pagination(
            get_page=get_page,
            ctx=ctx,
        )

        pagination_view.add_item(DeleteButton())

        await pagination_view.navegate()


    # Private functions

    async def _reply(
            self,
            ctx: commands.Context,
            text: str,
            /
    ) -> Message:

        text = f"**{text}**"        

        embed = self._gen_embed(
            description=text,
            author=ctx.author
        )

        

        return await ctx.reply(
            embed=embed
        )

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
                text=f"Requested by {author.display_name}",
                icon_url=author.display_avatar
            )
        else:
            embed._footer = {}

        return embed

    def _show_progress(
            self,
            position: int,
            length: int,
            /
    ) -> str:

        bar_length = 20
        progress = int((position / length) * bar_length)
        

        bar = '▬' * progress + '🔘' + '▬' * (bar_length - progress - 1)
        

        return f"[{bar}] `{self._milliseconds_to_time(position)}/{self._milliseconds_to_time(length)}`"


    def _get_cache(
            self,
            guild_id: int,
            value: str
    ) -> Union[None, Any]:

        cached_value: Dict = self.client.db._traverse_dict(
            self.cache,
            [guild_id, value],
            create_missing=True
        )


        return cached_value.get(value)

    def _milliseconds_to_time(
            self,
            ms: int, 
            /
    ) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60


        return f"{minutes:02}:{seconds:02}"


    def _time_to_milliseconds(
            self,
            time_str: str,
            /

    ) -> int:
        
        if ':' in time_str:
            parts = time_str.split(':')
        else:
            parts = [time_str]
        
        hours = 0
        minutes = 0
        seconds = 0
        
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
        elif len(parts) == 1:
            seconds = int(parts[0])

    
        total_milliseconds = (hours * 3600 * 1000) + (minutes * 60 * 1000) + (seconds * 1000)
        return total_milliseconds


async def setup(c):
    nodes = [
        Node(
            identifier=i.get("identifier"),
            password=i.get("password"),
            uri="{}://{}:{}".format(
                "https" if i.get("secure") else "http",
                i.get("host"),
                i.get("port"),
                
            ),
            
        )
        
        for i in LAVALINKS
    ]

    await Pool.connect(nodes=nodes, client=c, cache_capacity=100,)
    await c.add_cog(Music(c))
