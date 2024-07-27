from typing import Optional

from discord import app_commands
from discord.ext import commands

from bot.core import guilds
from bot.core.client import Client
from bot.templates.buttons import DeleteButton, QuitButton
from bot.templates.cogs import Cog
from bot.templates.embeds import SimpleEmbed
from bot.templates.views import Pagination, EmojisView
from bot.utils.functions import chunker, extract_emoji_info_from_text, remove_duplicates_preserve_order
from aiohttp import ClientSession
from discord.errors import HTTPException, Forbidden


class Hello(Cog):

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    
    # @commands.hybrid_command(
    #     name="hello",
    #     descriptio="Hello World!"
    # )
    # @app_commands.guilds(*guilds)
    # async def hello(
    #     self,
    #     ctx: commands.Context
    # ):
    #     async def get_page(index: int):

    #         chunks = chunker([str(i) for i in range(1000)], 20)
    #         embed = SimpleEmbed(
    #             client=self.client,
    #             description="\n".join(chunks[index])
    #         )

    #         kwrgs = {
    #             "embed": embed
    #         }

    #         return kwrgs, len(chunks)
            
        
    #     pagination_view = Pagination(
    #         get_page, 
    #         ctx=ctx
    #     )
        
    #     pagination_view.add_item(QuitButton())
    #     pagination_view.add_item(DeleteButton())

    #     await pagination_view.navegate()
    
    @commands.hybrid_command(
        name="steal",
        description="Will steal some emojis",
        with_app_command=True,
    )
    @app_commands.guilds(*guilds)
    @app_commands.describe(
        emojis = "Emojis to steal",
        force_add = "Will add emojis without showing the pagination",
        remove_duplicates = "Will remove duplicated emojis"
    )
    @commands.has_permissions(
        manage_emojis_and_stickers = True
    )
    async def steal(
        self,
        ctx: commands.Context,
        *,
        emojis: Optional[str] = None,
        force_add: Optional[bool] = False,
        remove_duplicates: Optional[bool] = True

    ): 
        extracted_emojis = []
        if ctx.message.reference and ctx.message.reference.message_id:
            refrenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            extracted_emojis = extract_emoji_info_from_text(refrenced_message.content)


        if emojis and extract_emoji_info_from_text(emojis) != []:
            extracted_emojis = extract_emoji_info_from_text(emojis)

        if remove_duplicates:
            extracted_emojis = remove_duplicates_preserve_order(extracted_emojis)

        async def get_page(index: int):

            extracted_emoji = extracted_emojis[index]

            embed = SimpleEmbed(
                client=self.client,
                title= "Emoji: {} | {}".format(
                    extracted_emoji["name"],
                    extracted_emoji["id"]
                )
            )
            embed.set_footer(
                text="Commanded by {}".format(
                    ctx.author
                ),
                icon_url=ctx.author.avatar
            )

            url = "https://cdn.discordapp.com/emojis/{}.png".format(
                extracted_emoji.get("id")
            )

            embed.set_image(url=url)

            kwrgs = {
                "embed": embed
            }

            return kwrgs, len(extracted_emojis)
        
        if extracted_emojis != []:
            if force_add:
                await ctx.send(
                    f"Started adding {len(extracted_emojis)} emojis"
                )
                for emoji in extracted_emojis:
                    success = 0
                    url = "https://cdn.discordapp.com/emojis/{}.png".format(emoji.get("id"))
                    async with ClientSession() as client:
                        async with client.get(url) as resp:
                            
                            if not resp.status == 200:
                                return await ctx.send(
                                    content="Failed to create emoji `{}`: Invalid emoji data".format(
                                        emoji.get("name")
                                    )
                                )
                            
                            data = await resp.read()
                            

                            try:
                                created_emoji = await ctx.guild.create_custom_emoji(
                                    name=emoji.get("name"),
                                    image=data
                                )
                            
                                emoji = f"<:{created_emoji.name}:{created_emoji.id}>"

                                if created_emoji.animated:
                                    emoji = f"<a:{created_emoji.name}:{created_emoji.id}>"

                                success+=1

                                await ctx.send(
                                    content="{} Created successfully".format(
                                        emoji
                                    )
                                )


                            except Forbidden:

                                await ctx.send(
                                    content="Failed to create emoji `{}`: 403 error occured".format(
                                        emoji.get("name")
                                    )
                                )

                            except HTTPException as e:
                                if e.code == 30008:

                                    await ctx.send(
                                        content="Failed to create emoji `{}`: The server has reached the maximum number of custom emojis".format(
                                            emoji.get("name")
                                        )
                                    )
                                
                                else:
                                    await ctx.send(
                                        content="Failed to create emoji `{}`: {}".format(
                                            emoji.get("name"),
                                            e.text
                                        )
                                    )

                else:
                    return await ctx.send(
                        content=f"The job is done\nsuccessfull: `{success}`\nunsuccessfull: `{len(extracted_emojis)-success}`"
                    )


            emojis_view = EmojisView(get_page, ctx=ctx, emojis_dict=extracted_emojis)
            emojis_view.add_item(QuitButton())

            return await emojis_view.navegate()
        
        return await ctx.reply("Didn't find any emoji!")
            
            

async def setup(c): await c.add_cog(Hello(c))