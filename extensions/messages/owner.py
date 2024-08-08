from ast import parse
from typing import Optional

import discord
from discord.ext import commands

from bot.core import Client, guilds
from bot.templates.buttons import DeleteButton
from bot.templates.cogs import Cog
from bot.templates.embeds import SimpleEmbed
from bot.templates.views import Pagination
from bot.utils.config import Emojis
from bot.utils.functions import chunker, insert_returns

_emojis = Emojis()

class Owner(Cog):

    def __init__(self, client: Client) -> None:
        
        self.emoji = _emojis.get("crown")

        super().__init__(client)
    



    @commands.command(
        name="eval",
        description="evals some code"
    )
    @commands.is_owner()
    async def eval(
        self,
        ctx: commands.Context,
        *,
        code: str,
    ):
        

        fn_name = "_eval_expr"
        cmd = code.strip("` ")

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = parse(body)
        body = parsed.body[0].body

        insert_returns(body)
        env = {
            'client': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__
        }
        
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = str((await eval(f"{fn_name}()", env)))

        if result == "None":
            return await ctx.message.add_reaction(_emojis.get("checkmark"))
        

        embed = SimpleEmbed(
            client=self.client,
            description=result[:2000:]
        )

        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar
        )


        if len(result) > 2000:

            async def get_page(
                    index: int
            ):
                chunks = chunker(result, 2000)


                embed.description = chunks[index]


                kwrgs = {
                    "embed": embed,
                    "silent": True
                }

                return kwrgs, len(chunks)

            pagination_view = Pagination(
                get_page=get_page,
                ctx=ctx
            )


            return await pagination_view.navegate()
        
        await ctx.reply(
            embed=embed,
            silent=True
        )



async def setup(c):

    await c.add_cog(Owner(c))