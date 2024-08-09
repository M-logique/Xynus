from discord import Interaction, TextStyle
from discord.ui import Modal, TextInput, View
from discord import User
from time import time


class PaginationIndexModal(Modal):

    max_length: int
    

    index = TextInput(
        label="index of the page",
        style=TextStyle.short,
        max_length=100,
        min_length=1,
        required=True
    )

    def __init__(
            self,
            view: View
    ) -> None:
        super().__init__(
            title="Index?",
            timeout=120,
            custom_id="index-modal"
        )

        self.view = view


        

    async def on_submit(self, interaction: Interaction):

        value = self.index.value

        if not value.isdigit():
            return await interaction.response.send_message("Value should be an integer", ephemeral=True)
        
        value = int(value)

        if value > self.view.total_pages or value < 1:
            return await interaction.response.send_message("Provided index is out of range", ephemeral=True)



        self.view.index = value -1
        return await self.view.edit_page(interaction)
    

class WhisperModal(Modal):

    text = TextInput(
        label="Whisper Text",
        placeholder="What do you want to tell them?",
        max_length=2000,
        min_length=1
    )

    def __init__(
            self,
            target: User
    ) -> None:
        
        self.target = target

        super().__init__(
            title="Whisper",
            timeout=120,
            custom_id="whisper"
        )
    
    async def on_submit(self, interaction: Interaction) -> None:
        from .views import WhisperView

        
        await interaction.response.send_message(
            content="Sent the whisper message",
            ephemeral=True
        )

        if interaction.message:
            await interaction.message.delete()


        view = WhisperView(
            target=self.target,
            author=interaction.user,
            text=self.text.value
        )

        expiry_time = int(time() + 15 * 60)

        view.message = await interaction.channel.send(
            content=f":eyes: {self.target.mention}, You have a very very very secret message from {interaction.user.mention}!\nThis message will expire <t:{expiry_time}:R>.",
            view=view
        )