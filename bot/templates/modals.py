from re import compile, match
from time import time
from typing import TYPE_CHECKING, Self

from discord import (Color, Embed, Forbidden, HTTPException, Interaction,
                     Message, NotFound, TextStyle, User)
from discord.ui import Modal, TextInput, View

from .embeds import MappingInfoEmbed
from ..utils.config import Emojis
from ..utils.functions import to_boolean, find_command_name
from .exceptions import InvalidModalField

if TYPE_CHECKING:
    from .views import EmbedEditor
    from .views import MappingEditView

_emojis = Emojis()
checkmark = _emojis.get("checkmark")


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


class CommandEditModal(Modal, title="Edit the command"):
    command = TextInput(
        label="Command text",
        placeholder="Your shitty command goes here",
        max_length=4000,
        style=TextStyle.paragraph,
        required=True
    )

    def __init__(self, prev_view: "MappingEditView", /):
        self.prev_view = prev_view
        self.command.default = prev_view.command

        super().__init__(timeout=120)

    async def on_submit(self, interaction: Interaction) -> None:
        command_name = find_command_name(self.command.value)

        
        if not interaction.client.get_command(command_name):
            return await interaction.response.send_message(
                f"Cannot map `{command_name[:20:]}` as it is not a valid command.",
                ephemeral=True
            )
        
        
        self.prev_view.command = self.command.value
        self.prev_view.update_save_button()
        await interaction.response.edit_message(
            view=self.prev_view,
            embed=MappingInfoEmbed(
                interaction,
                self.prev_view.trigger,
                self.command.value,
                self.prev_view.prev_view.created_at,
            )
        )


class TriggerEditModal(Modal, title="Edit the trigger"):
    trigger = TextInput(
        label="trigger text",
        placeholder="Your shitty trigger goes here",
        max_length=20,
        required=True
    )

    def __init__(self, prev_view: "MappingEditView", /):
        self.prev_view = prev_view
        self.trigger.default = prev_view.trigger
        
        super().__init__(timeout=120)

    async def on_submit(self, interaction: Interaction) -> None:
        trigger = self.trigger.value.lower().replace(" ", "")

        sticked_command = interaction.client.get_command(trigger)
        original_message = None
        if sticked_command:
            
            if sticked_command.name == self.prev_view.prev_view.mappings.name:
                return await interaction.response.send_message(
                    f"🤔 **for some reasons, you can't add {trigger!r} as your trigger!**",
                    ephemeral=True
                )
            
            
            else:
                from .views import ConfirmationView
                from .embeds import ConfirmationEmbed

                view = ConfirmationView(
                    interaction, 
                    owner_id=interaction.user.id,
                    timeout=30
                )

                text = (
                    "**You are using one of the bot's commands as a trigger. "
                    "This will cause the original command to stop working. "
                    "Are you sure you want to use this trigger?**"
                )

                original_message = interaction.message

                await interaction.response.send_message(
                    embed=ConfirmationEmbed(
                        text,
                        30
                    ),
                    view=view,
                    ephemeral=True
                )

                await view.wait()
                if not view.value: return
        
            
        
        self.prev_view.trigger = self.trigger.value
        self.prev_view.update_save_button()
        await (
            interaction.response.edit_message 
            if not original_message and not interaction.response.is_done()
            else original_message.edit
        )(
            view=self.prev_view,
            embed=MappingInfoEmbed(
                interaction,
                trigger,
                self.prev_view.command,
                self.prev_view.prev_view.created_at,
            )
        )


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
            content=f"{checkmark} | Sent in {interaction.channel.mention}",
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
            content=f":eyes: {self.target.mention}, You have a very very very secret message from {interaction.user.mention}!\nYou can only use the button until <t:{expiry_time}:t>.",
            view=view
        )


URL_REGEX = compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

class EmbedBaseModal(Modal):
    def __init__(self, parent_view: "EmbedEditor") -> None:
        self.parent_view = parent_view
        self.update_defaults(parent_view.embed)
        super().__init__()

    def update_embed(self) -> None:
        raise NotImplementedError

    def update_defaults(self, embed: Embed):
        return

    async def on_error(self, interaction: Interaction, error: Exception, /) -> None:
        if isinstance(error, InvalidModalField):
            await self.parent_view.update_buttons()
            await interaction.response.edit_message(embed=self.parent_view.current_embed, view=self.parent_view)
            await interaction.followup.send(str(error), ephemeral=True)
            return
        await super().on_error(interaction, error)

    async def on_submit(self, interaction: Interaction, /) -> None:
        self.update_embed()
        await self.parent_view.update_buttons()
        await interaction.response.edit_message(embed=self.parent_view.current_embed, view=self.parent_view)



class EditEmbedModal(EmbedBaseModal, title='Editing the embed:'):
    _title = TextInput[Self](
        label='Embed Title', placeholder='Leave any field empty to remove it', max_length=256, required=False
    )
    description = TextInput[Self](
        label='Embed Description',
        placeholder='Any text, up to 4,000 characters.\n\nEmbeds can have a shared total of 6,000 characters!',
        style=TextStyle.long,
        required=False,
    )
    image = TextInput[Self](label='Embed Image URL', placeholder='Must be HTTP(S) format.', required=False)
    thumbnail = TextInput[Self](
        label='Thumbnail Image URL', placeholder='Must be HTTP(S) format.', required=False
    )
    color = TextInput[Self](
        label='Embed Color', placeholder='Hex [#FFFFFF] or RGB [rgb(num, num, num)] only', required=False
    )

    def update_defaults(self, embed: Embed):
        self._title.default = embed.title
        self.description.default = embed.description
        self.image.default = embed.image.url
        self.thumbnail.default = embed.thumbnail.url
        if embed.color:
            self.color.default = str(embed.color)

    def update_embed(self):
        self.parent_view.embed.title = self._title.value.strip() or None
        self.parent_view.embed.description = self.description.value.strip() or None
        failed: list[str] = []
        if self.color.value:
            try:
                color = Color.from_str(self.color.value)
                self.parent_view.embed.color = color
            except (ValueError, IndexError):
                failed.append('Invalid Color given!')
        else:
            self.parent_view.embed.color = None

        sti = self.image.value.strip()
        if URL_REGEX.fullmatch(sti):
            self.parent_view.embed.set_image(url=sti)
        elif sti:
            failed.append('Image URL did not match the http/https format')
        else:
            self.parent_view.embed.set_image(url=None)

        sti = self.thumbnail.value.strip()
        if URL_REGEX.fullmatch(sti):
            self.parent_view.embed.set_thumbnail(url=sti)
        elif sti:
            failed.append('Thumbnail URL did not match the http/https format')
        else:
            self.parent_view.embed.set_thumbnail(url=None)
        if failed:
            raise InvalidModalField('\n'.join(failed))
        

class EditAuthorModal(EmbedBaseModal, title='Editing the embed author:'):
    name = TextInput[Self](
        label='Author name', max_length=256, placeholder='Leave any field empty to remove it', required=False
    )
    url = TextInput[Self](label="Author URL", placeholder='Must be HTTP(S) format.', required=False)
    image = TextInput[Self](label='Author Icon URL', placeholder='Must be HTTP(S) format.', required=False)

    def update_defaults(self, embed: Embed):
        self.name.default = embed.author.name
        self.url.default = embed.author.url
        self.image.default = embed.author.icon_url

    def update_embed(self):
        author = self.name.value.strip()
        if not author:
            self.parent_view.embed.remove_author()

        failed: list[str] = []

        image_url = None
        sti = self.image.value.strip()
        if URL_REGEX.fullmatch(sti):
            if not author:
                failed.append(
                    'Cannot add image. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            image_url = sti
        elif sti:
            if not author:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            failed.append('Image URL did not match the http/https format.')

        url = None
        sti = self.url.value.strip()
        if URL_REGEX.fullmatch(sti):
            if not author:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            url = sti
        elif sti:
            if not author:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            failed.append('URL did not match the http/https format.')

        if author:
            self.parent_view.embed.set_author(name=author, url=url, icon_url=image_url)

        if failed:
            raise InvalidModalField('\n'.join(failed))
        

class EditFooterModal(EmbedBaseModal, title='Editing the embed author:'):
    text = TextInput[Self](
        label='Footer text', max_length=256, placeholder='Leave any field empty to remove it', required=False
    )
    image = TextInput[Self](label='Footer icon URL', placeholder='Must be HTTP(S) format.', required=False)

    def update_defaults(self, embed: Embed):
        self.text.default = embed.footer.text
        self.image.default = embed.footer.icon_url

    def update_embed(self):
        text = self.text.value.strip()
        if not text:
            self.parent_view.embed.remove_author()

        failed: list[str] = []

        image_url = None
        sti = self.image.value.strip()
        if URL_REGEX.fullmatch(sti):
            if not text:
                failed.append(
                    'Cannot add image. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            image_url = sti
        elif sti:
            if not text:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            failed.append('Image URL did not match the http/https format.')

        if text:
            self.parent_view.embed.set_footer(text=text, icon_url=image_url)

        if failed:
            raise InvalidModalField('\n'.join(failed))
        
class AddFieldModal(EmbedBaseModal, title='Add a field'):
    name = TextInput[Self](label='Field Name', max_length=256)
    value = TextInput[Self](label='Field Value', max_length=1024, style=TextStyle.paragraph)
    inline = TextInput[Self](
        label='Is inline?', placeholder='[ "Yes" | "No" ] (Default: Yes)', max_length=4, required=False
    )
    index = TextInput[Self](
        label='Index (where to place this field)',
        placeholder='Number between 1 and 25. Default: 25 (last)',
        max_length=2,
        required=False,
    )

    def update_embed(self):
        failed: list[str] = []

        name = self.name.value.strip()
        if not name:
            raise InvalidModalField('Name and Value are required.')
        value = self.value.value.strip()
        if not value:
            raise InvalidModalField('Name and Value are required.')
        _inline = self.inline.value.strip()
        _idx = self.index.value.strip()

        inline = True
        if _inline:
            try:
                inline = to_boolean(_inline)
            except Exception as e:
                failed.append(str(e))

        if _idx:
            try:
                index = int(_idx) - 1
                self.parent_view.embed.insert_field_at(index=index, name=name, value=value, inline=inline)
            except:
                failed.append('Invalid index! (not a number)')
                self.parent_view.embed.add_field(name=name, value=value, inline=inline)
        else:
            self.parent_view.embed.add_field(name=name, value=value, inline=inline)

        if failed:
            raise InvalidModalField('\n'.join(failed))
        

class EditFieldModal(EmbedBaseModal):
    name = TextInput[Self](label='Field Name', max_length=256)
    value = TextInput[Self](label='Field Value', max_length=1024, style=TextStyle.paragraph)
    inline = TextInput[Self](
        label='Is inline?', placeholder='[ "Yes" | "No" ] (Default: Yes)', max_length=4, required=False
    )
    new_index = TextInput[Self](
        label='Index (where to place this field)',
        placeholder='Number between 1 and 25. Default: 25 (last)',
        max_length=2,
        required=False,
    )

    def __init__(self, parent_view: "EmbedEditor", index: int) -> None:
        self.field = parent_view.embed.fields[index]
        self.title = f'Editing field number {index}'
        self.index = index

        super().__init__(parent_view)

    def update_defaults(self, embed: Embed):
        self.name.default = self.field.name
        self.value.default = self.field.value
        self.inline.default = 'Yes' if self.field.inline else 'No'
        self.new_index.default = str(self.index + 1)

    def update_embed(self):
        failed = None

        name = self.name.value.strip()
        if not name:
            raise InvalidModalField('Name and Value are required.')
        value = self.value.value.strip()
        if not value:
            raise InvalidModalField('Name and Value are required.')
        _inline = self.inline.value.strip()

        inline = True
        if _inline:
            try:
                inline = to_boolean(_inline)
            except Exception as e:
                failed = str(e)
        if self.new_index.value.isdigit():
            self.parent_view.embed.remove_field(self.index)
            self.parent_view.embed.insert_field_at(int(self.new_index.value) - 1, name=name, value=value, inline=inline)
        else:
            self.parent_view.embed.set_field_at(self.index, name=name, value=value, inline=inline)

        if failed:
            raise InvalidModalField(failed)
        

class AddFieldModal(EmbedBaseModal, title='Add a field'):
    name = TextInput[Self](label='Field Name', max_length=256)
    value = TextInput[Self](label='Field Value', max_length=1024, style=TextStyle.paragraph)
    inline = TextInput[Self](
        label='Is inline?', placeholder='[ "Yes" | "No" ] (Default: Yes)', max_length=4, required=False
    )
    index = TextInput[Self](
        label='Index (where to place this field)',
        placeholder='Number between 1 and 25. Default: 25 (last)',
        max_length=2,
        required=False,
    )

    def update_embed(self):
        failed: list[str] = []

        name = self.name.value.strip()
        if not name:
            raise InvalidModalField('Name and Value are required.')
        value = self.value.value.strip()
        if not value:
            raise InvalidModalField('Name and Value are required.')
        _inline = self.inline.value.strip()
        _idx = self.index.value.strip()

        inline = True
        if _inline:
            try:
                inline = to_boolean(_inline)
            except Exception as e:
                failed.append(str(e))

        if _idx:
            try:
                index = int(_idx) - 1
                self.parent_view.embed.insert_field_at(index=index, name=name, value=value, inline=inline)
            except:
                failed.append('Invalid index! (not a number)')
                self.parent_view.embed.add_field(name=name, value=value, inline=inline)
        else:
            self.parent_view.embed.add_field(name=name, value=value, inline=inline)

        if failed:
            raise InvalidModalField('\n'.join(failed))


class LoadMessageModal(EmbedBaseModal, title="Loading embed from its url"):

    url = TextInput(
        label="Url of message",
        placeholder="http(s)://discord.com/channels/.../.../...",
        max_length=100,
        required=True
    )

    def update_embed(self) -> None:
        
        msg: Message = self.loaded_message
        self.parent_view.embed = msg.embeds[0]


    async def on_submit(self, interaction: Interaction) -> None:

        pattern = r"^https?://discord\.com/channels/(\d+)/(\d+)/(\d+)$"
        matched = match(pattern, self.url.value)

        original_message = interaction.message
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not matched:
            return await interaction.edit_original_response(content="Invalid url provided")

        
        guild_id, channel_id, message_id = map(lambda _: int(_), matched.groups())


        if not guild_id == interaction.guild_id:
            return await interaction.edit_original_response(content="Invalid guild provided")
        
        channel = interaction.guild.get_channel(channel_id)

        if not channel:
            await interaction.edit_original_response(content="Didn't find the channel")
        
        try:
            message = await channel.fetch_message(message_id)

            if not message.embeds:
                return await interaction.edit_original_response(content="Didn't find any embed in this message")
            
            self.loaded_message = message
        
        except (Forbidden, HTTPException, NotFound):
            await interaction.edit_original_response(content="Failed to fetch the message")
        

        
        self.update_embed()
        await self.parent_view.update_buttons()


        await original_message.edit(embed=self.parent_view.current_embed, view=self.parent_view)
        await interaction.edit_original_response(content="Loaded!")

        