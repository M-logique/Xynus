from discord import Interaction, TextStyle
from discord.ui import Modal, TextInput, View


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
    