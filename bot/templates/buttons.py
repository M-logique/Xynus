from typing import Any as _Any

from discord import ButtonStyle as _ButtonStyle
from discord import Forbidden as _Forbidden
from discord import Interaction as _Interaction
from discord import NotFound as _NotFound
from discord.ui import Button as _Button

from ..utils.config import Emojis
from ..utils.functions import disable_all_items as _disable_all_items

emojis = Emojis()

class QuitButton(_Button):

    def __init__(
            self
    ):
        super().__init__(
            label="Quit",
            style=_ButtonStyle.danger,
            custom_id="quit"
        )

    async def callback(self, interaction: _Interaction) -> _Any:
        await interaction.response.edit_message()
        await _disable_all_items(self.view)

class DeleteButton(_Button):

    def __init__(
            self
    ):
        super().__init__(
            style=_ButtonStyle.red,
            emoji=emojis.get("trashcan")
        )
        
    
    async def callback(self, interaction: _Interaction) -> _Any:


        await interaction.response.edit_message()

        message = interaction.message



        await interaction.delete_original_response()
        
        if message.reference:
            try:
                refrenced_message = await interaction.channel.fetch_message(
                    message.reference.message_id
                )
                await refrenced_message.delete()

            except (_Forbidden, _NotFound):
                pass
            