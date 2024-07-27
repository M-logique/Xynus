from typing import Any, Callable, Dict, Optional

from aiohttp import ClientSession
from discord import Button, ButtonStyle, Emoji, Interaction
from discord.errors import Forbidden, HTTPException
from discord.ext import commands
from discord.ui import View as _View
from discord.ui import button

from ..utils.config import Emojis
from ..utils.functions import disable_all_items as _disable_all_items

emojis = Emojis()

class BaseView(_View):

    def __init__(self):

        self.message = None
        super().__init__(timeout=120)

    
    async def on_timeout(self) -> None:
        return await _disable_all_items(self)




class Pagination(_View):
    def __init__(
            self,
            get_page: Callable,
            interaction: Optional[Interaction] = None,
            ctx: Optional[commands.Context] = None

    ):


        if interaction:
            self.reply = interaction.response.send_message
            self.user = interaction.user
            self.defer = interaction.response.defer
            self.message = interaction.original_response
        
        if ctx:
            self.reply = ctx.reply
            self.user = ctx.author
            self.defer = ctx.defer

        self.get_page = get_page
        self.total_pages: Optional[int] = None
        self.index = 0
        self.message = None

        super().__init__(timeout=120)



    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user == self.user:
            return True
        else:
            await interaction.response.edit_message()
            return False

    async def navegate(self, ephemeral: Optional[bool] = False):

        if ephemeral:
            await self.defer(ephemeral=True)

        kwrgs, self.total_pages = await self.get_page(self.index)

        self.update_buttons()
        
        if self.total_pages == 1:

            for item in self.children:
                if item.row == 0:
                    item.disabled = True
            

        
        msg = await self.reply(**kwrgs, view=self)

        if not self.message:
            self.message = msg
        else:
            self.message = await self.message()


    async def edit_page(self, interaction: Interaction):
        kwrgs, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await interaction.response.edit_message(**kwrgs, view=self)

    def update_buttons(self):
        
        self.children[0].disabled = self.index == 0
        self.children[1].disabled = self.index == 0

        self.children[2].label = "{} / {}".format(self.index + 1, self.total_pages)

        self.children[3].disabled = self.index == self.total_pages -1
        self.children[4].disabled = self.index == self.total_pages -1

    # @button(label="<<", style=ButtonStyle.blurple, disabled=True)
    @button(emoji=emojis.pagination.get("start"), style=ButtonStyle.green, disabled=True, row=0)
    async def start(self, interaction: Interaction, button: Button):
        self.index = 0

        await self.edit_page(interaction)

    # @button(label="<", style=ButtonStyle.blurple)
    @button(emoji=emojis.pagination.get("previous"), style=ButtonStyle.green, disabled=True, row=0)
    async def previous(self, interaction: Interaction, button: Button):
        self.index -= 1
        await self.edit_page(interaction)

    @button(label="1 / 1", style=ButtonStyle.grey, row=0)
    async def index_button(
        self,
        interaction: Interaction,
        button: Button
    ):
        from .modals import PaginationIndexModal

        modal = PaginationIndexModal(self)

        return await interaction.response.send_modal(modal)

    # @button(label=">", style=ButtonStyle.blurple)
    @button(emoji=emojis.pagination.get("next"), style=ButtonStyle.green, row=0)
    async def next(self, interaction: Interaction, button: Button):
        self.index += 1
        await self.edit_page(interaction)

    # @button(label=">>", style=ButtonStyle.blurple)
    @button(emoji=emojis.pagination.get("end"), style=ButtonStyle.green, row=0)
    async def end(self, interaction: Interaction, button: Button):

        self.index = self.total_pages -1

        await self.edit_page(interaction)
    

    async def on_timeout(self):
        await _disable_all_items(self)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1



class EmojisView(Pagination):

    def __init__(
            self,
            get_page: Callable,
            emojis_dict: Dict,
            interaction: Optional[Interaction] = None,
            ctx: Optional[commands.Context] = None,
    ):
        self.emojis = emojis_dict

        super().__init__(get_page, interaction, ctx)
    
    @button(label="Steal this one", style=ButtonStyle.green, emoji=emojis.global_emojis["hand"])
    async def add_emoji(
        self,
        interaction: Interaction,
        button: Button
    ):
        await interaction.response.defer(
            thinking=True
        )

        check_mark = emojis.global_emojis["checkmark"]
        cross_mark = emojis.global_emojis["crossmark"]

        emoji = self.emojis[self.index]
        url = "https://cdn.discordapp.com/emojis/{}.png".format(emoji.get("id"))
        async with ClientSession() as client:
            async with client.get(url) as resp:
                
                if not resp.status == 200:
                    return await interaction.edit_original_response(
                        content="{} | Failed to steal emoji `{}`: Invalid emoji data".format(
                            cross_mark,
                            emoji.get("name")
                        )
                    )
                
                data = await resp.read()
                
                

                try:
                    created_emoji = await interaction.guild.create_custom_emoji(
                        name=emoji.get("name"),
                        image=data
                    )
                
                    emoji = f"<:{created_emoji.name}:{created_emoji.id}>"

                    if created_emoji.animated:
                        emoji = f"<a:{created_emoji.name}:{created_emoji.id}>"


                    await interaction.edit_original_response(
                        content="{} | Successfully stole emoji: {}".format(
                            check_mark,
                            emoji
                        )
                    )

                except Forbidden:

                    await interaction.edit_original_response(
                        content="{} | Failed to create emoji `{}`: 403 error occured".format(
                            cross_mark,
                            emoji.get("name")
                        )
                    )

                except HTTPException as e:
                    if e.code == 30008:

                        await interaction.edit_original_response(
                            content="{} | Failed to steal emoji `{}`: The server has reached the maximum number of custom emojis".format(
                                cross_mark,
                                emoji.get("name")
                            )
                        )
                    
                    else:
                        await interaction.edit_original_response(
                            content="{} | Failed to steal emoji `{}`: {}".format(
                                cross_mark,
                                emoji.get("name"),
                                e.text
                            )
                        )

    