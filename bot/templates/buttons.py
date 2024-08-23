from typing import TYPE_CHECKING
from typing import Any as _Any
from typing import Optional, Type, Union

from discord import ButtonStyle as _ButtonStyle
from discord import DiscordException, Emoji
from discord import Forbidden as _Forbidden
from discord import Interaction as _Interaction
from discord import NotFound as _NotFound
from discord import PartialEmoji
from discord.ui import Button as _Button

from ..utils.config import Emojis
from ..utils.functions import disable_all_items as _disable_all_items

if TYPE_CHECKING:

    from .modals import EmbedBaseModal
    from .views import EmbedEditor

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


        await interaction.response.defer()

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
            


class EditWithModalButton(_Button['EmbedEditor']):
    def __init__(
        self,
        modal: Type["EmbedBaseModal"],
        /,
        *,
        style: _ButtonStyle = _ButtonStyle.secondary,
        label: Optional[str] = None,
        disabled: bool = False,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
        row: Optional[int] = None,
    ):
        self.modal = modal
        super().__init__(style=style, label=label, disabled=disabled, emoji=emoji, row=row)

    async def callback(self, interaction: _Interaction):
        if not self.view:
            raise DiscordException('No view was found attached to this modal.')
        await interaction.response.send_modal(self.modal(self.view))

