from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple,
                    Union, overload)

from asyncpg.pool import Pool
from discord import (AllowedMentions, Embed, File, Forbidden, Interaction,
                     Message, MessageReference, NotFound, PartialMessage, User)
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.context import MISSING
from discord.ext.commands.view import StringView
from discord.poll import Poll
from discord.sticker import GuildSticker, StickerItem
from discord.ui import View
from discord.utils import cached_property

from .embeds import ConfirmationEmbed
from .views import ConfirmationView, ViewWithDeleteButton

if TYPE_CHECKING:
    from ..core import Xynus

# A large amount of code + ideas have been transferred from the HideoutManager project
#     https://github.com/DuckBot-Discord/duck-hideout-manager-bot/blob/main/utils/bot_bases/context.py


class XynusContext(commands.Context):

    __slots__: Tuple[str, ...] = (
        "bot",
        "client",
        "db"
    )

    def __init__(
        self,
        *,
        message: Message,
        bot: "Xynus",
        view: StringView,
        args: List[Any] = MISSING,
        kwargs: Dict[str, Any] = MISSING,
        prefix: Optional[str] = None,
        command: Optional[commands.Command[Any, ..., Any]] = None,
        invoked_with: Optional[str] = None,
        invoked_parents: List[str] = MISSING,
        invoked_subcommand: Optional[commands.Command[Any, ..., Any]] = None,
        subcommand_passed: Optional[str] = None,
        command_failed: bool = False,
        current_parameter: Optional[commands.Parameter] = None,
        current_argument: Optional[str] = None,
        interaction: Optional[Interaction] = None,
    ):
        """
        Initializes the XynusContext with various parameters.

        :param message: The message that initiated the context.
        :type message: :class:`discord.Message`
        :param bot: The bot instance handling this context.
        :type bot: :class:`Xynus`
        :param view: The string view used for command parsing.
        :type view: :class:`discord.ext.commands.view.StringView`
        :param args: Positional arguments for the command.
        :type args: list of :class:`Any`
        :param kwargs: Keyword arguments for the command.
        :type kwargs: dict of :class:`str` to :class:`Any`
        :param prefix: The prefix used for the command.
        :type prefix: Optional[:class:`str`]
        :param command: The command that was invoked.
        :type command: Optional[:class:`discord.ext.commands.Command`]
        :param invoked_with: The exact string used to invoke the command.
        :type invoked_with: Optional[:class:`str`]
        :param invoked_parents: List of parent commands invoked.
        :type invoked_parents: list of :class:`str`
        :param invoked_subcommand: The subcommand that was invoked.
        :type invoked_subcommand: Optional[:class:`discord.ext.commands.Command`]
        :param subcommand_passed: The subcommand passed if any.
        :type subcommand_passed: Optional[:class:`str`]
        :param command_failed: Indicates if the command failed.
        :type command_failed: bool
        :param current_parameter: The current command parameter.
        :type current_parameter: Optional[:class:`discord.ext.commands.Parameter`]
        :param current_argument: The current argument being processed.
        :type current_argument: Optional[:class:`str`]
        :param interaction: The interaction associated with the command.
        :type interaction: Optional[:class:`discord.Interaction`]
        """

        self.bot: "Xynus" = bot
        self.client: "Xynus" = bot
        self.db = bot.db
        super().__init__(message=message, bot=bot, view=view, args=args, kwargs=kwargs, prefix=prefix, command=command, invoked_with=invoked_with, invoked_parents=invoked_parents, invoked_subcommand=invoked_subcommand, subcommand_passed=subcommand_passed, command_failed=command_failed, current_parameter=current_parameter, current_argument=current_argument, interaction=interaction)


    @overload
    async def send(  # type: ignore
        self,
        content: Optional[str] = None,
        *,
        tts: bool = False,
        embed: Optional[Embed] = None,
        embeds: Optional[Sequence[Embed]] = None,
        file: Optional[File] = None,
        files: Optional[Sequence[File]] = None,
        delete_after: Optional[float] = None,
        nonce: Optional[Union[str, int]] = None,
        allowed_mentions: Optional[AllowedMentions] = None,
        reference: Optional[Union[Message, MessageReference, PartialMessage]] = None,
        mention_author: Optional[bool] = None,
        view: Optional[View] = None,
        suppress_embeds: bool = False,
        ephemeral: bool = False,
        delete_button: bool = True,
        **kwargs: Any
    ) -> Message:
        ...

    async def send(self, content: str | None = None, **kwargs: Any) -> Message:
        """|coro|

        Sends a message to the invoking context's channel.

        :param content: The content of the message to send.
        :type content: Optional[:class:`str`]
        :param tts: Whether to send the message as a Text-to-Speech.
        :type tts: bool
        :param embed: An embed to include with the message.
        :type embed: Optional[:class:`discord.Embed`]
        :param embeds: A list of embeds to include with the message.
        :type embeds: Optional[Sequence[:class:`discord.Embed`]]
        :param file: A file to attach to the message.
        :type file: Optional[:class:`discord.File`]
        :param files: A list of files to attach to the message.
        :type files: Optional[Sequence[:class:`discord.File`]]
        :param delete_after: Number of seconds before deleting the message.
        :type delete_after: Optional[float]
        :param nonce: A unique ID for the message.
        :type nonce: Optional[Union[:class:`str`, :class:`int`]]
        :param allowed_mentions: Mentions allowed in the message.
        :type allowed_mentions: Optional[:class:`discord.AllowedMentions`]
        :param reference: Message to reference.
        :type reference: Optional[Union[:class:`discord.Message`, :class:`discord.MessageReference`, :class:`discord.PartialMessage`]]
        :param mention_author: Whether to mention the author of the message.
        :type mention_author: Optional[bool]
        :param view: A view to attach to the message.
        :type view: Optional[:class:`discord.ui.View`]
        :param suppress_embeds: Whether to suppress embeds in the message.
        :type suppress_embeds: bool
        :param ephemeral: Whether the message is ephemeral.
        :type ephemeral: bool

        :raises ValueError: If both ``embed`` and ``embeds`` are provided.
        :raises TypeError: If both ``view`` and ``delete_button`` are provided.

        :returns: The message that was created.
        :rtype: :class:`discord.Message`
        """

        if kwargs.get('embed') and kwargs.get('embeds'):
            raise ValueError('Cannot send both embed and embeds')

        embeds: Sequence[Embed] = kwargs.pop('embeds', []) or ([kwargs.pop('embed')] if kwargs.get('embed', None) else [])
        if embeds:
            for embed in embeds:
                if embed.color is None:
                    # Made this the bot's vanity colour, although we'll
                    # be keeping self.color for other stuff like userinfo
                    embed.color = self.bot.color

            kwargs['embeds'] = embeds

        if kwargs.get("delete_button"):
            if kwargs.get("view"):
                raise ValueError("'delete_button' and 'view' cannot be passed together.")
            
            kwargs["view"] = ViewWithDeleteButton(self.author)
            del kwargs["delete_button"]

        try:
            if isinstance(kwargs.get("view"), ViewWithDeleteButton):
                msg = await super().send(content, **kwargs)
                kwargs["view"].message = msg
                return msg
            
            return await super().send(content, **kwargs)
    
        except (Forbidden, HTTPException):
            pass # type: ignore


    @overload
    async def reply( # type: ignore
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embed: Embed = ...,
        file: File = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    @overload
    async def reply( # type: ignore
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embed: Embed = ...,
        files: Sequence[File] = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    @overload
    async def reply( # type: ignore
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[Embed] = ...,
        file: File = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    @overload
    async def reply( # type: ignore
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[Embed] = ...,
        files: Sequence[File] = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
        poll: Poll = ...,
    ) -> Message:
        ...

    async def reply(self, content: Optional[str] = None, **kwargs: Any) -> Message:
        """|coro|

        A shortcut method to :meth:`send` to reply to the :class:`discord.Message` referenced by this context.

        :param content: The content of the reply message.
        :type content: Optional[:class:`str`]
        :param tts: Whether to send the reply as a Text-to-Speech.
        :type tts: bool
        :param embed: An embed to include with the reply.
        :type embed: Optional[:class:`discord.Embed`]
        :param file: A file to attach to the reply.
        :type file: Optional[:class:`discord.File`]
        :param stickers: Stickers to include in the reply.
        :type stickers: Optional[Sequence[Union[:class:`discord.GuildSticker`, :class:`discord.StickerItem`]]]
        :param delete_after: Number of seconds before deleting the reply.
        :type delete_after: Optional[float]
        :param nonce: A unique ID for the reply.
        :type nonce: Optional[Union[:class:`str`, :class:`int`]]
        :param allowed_mentions: Mentions allowed in the reply.
        :type allowed_mentions: Optional[:class:`discord.AllowedMentions`]
        :param reference: Message to reference.
        :type reference: Optional[Union[:class:`discord.Message`, :class:`discord.MessageReference`, :class:`discord.PartialMessage`]]
        :param mention_author: Whether to mention the author of the message.
        :type mention_author: Optional[bool]
        :param view: A view to attach to the reply.
        :type view: Optional[:class:`discord.ui.View`]
        :param suppress_embeds: Whether to suppress embeds in the reply.
        :type suppress_embeds: bool
        :param ephemeral: Whether the reply is ephemeral.
        :type ephemeral: bool
        :param silent: Whether to suppress the reply's content.
        :type silent: bool
        :param poll: A poll to include with the reply.
        :type poll: Optional[:class:`discord.Poll`]

        :raises ValueError: If the ``files`` list is not of the appropriate size.
        :raises TypeError: If both ``file`` and ``files`` are specified.
        :raises discord.HTTPException: If sending the reply fails.
        :raises discord.Forbidden: If you lack permissions to send the reply.

        :returns: The message that was sent.
        :rtype: :class:`discord.Message`
        """

        
        
        try:
            await self.channel.fetch_message(self.message.id)
            return await super().reply(
                content=content,
                **kwargs
            )
        except (NotFound, HTTPException):
            # send directly if failed to reply
            return await self.send(content, **kwargs)

    async def confirm(
        self,
        text: Optional[str] = None,
        /,
        *,
        owner: Optional[int] = None,
        timeout: int = 30,
    ):
        """|coro|

        Sends a confirmation message and waits for user response.

        :param text: The confirmation message to display.
        :type text: Optional[:class:`str`]
        :param owner: The ID of the user who can confirm.
        :type owner: Optional[int]
        :param timeout: The time in seconds to wait for a response.
        :type timeout: int

        :returns: The value of the user's response.
        :rtype: Optional[bool]
        """

        embed = ConfirmationEmbed(text, timeout)
        view = ConfirmationView(ctx=self, owner_id=owner, timeout=timeout)
        try:
            view.message = await self.send(
                embed=embed,
                view=view
            )
            await view.wait()
            return view.value
        
        except HTTPException:
            return None
            

    @cached_property
    def reference(self) -> Optional[Message]:
        """
        Returns the referenced message if available.

        :returns: The referenced message or None if not referenced.
        :rtype: Optional[:class:`discord.Message`]
        """

        if self.message:
            if self.message.reference:
                resolved = self.message.reference.resolved
                if isinstance(resolved, Message):
                    return resolved


        return None
    
    

    def load_query(
            self,
            name: str
    ):
        """
        Loads an SQL query from a file.

        :param name: The name of the SQL file containing the query.
        :type name: str

        :returns: The SQL query as a string.
        :rtype: str
        """

        return self.bot._load_query(name)
    
    @property
    def created_at(self):
        """
        Returns the creation time of the message.

        :returns: The creation time of the message.
        :rtype: :class:`datetime.datetime`
        """

        return self.message.created_at

    @cached_property
    def user(self) -> User:
        """
        Returns the author of the message.

        :returns: The author of the message.
        :rtype: :class:`discord.User`
        """

        return self.author
    
    @property
    def channel_id(self) -> int:
        """
        Returns the ID of the channel where the message was sent.

        :returns: The channel ID.
        :rtype: int
        """

        return self.channel.id
    
    @cached_property
    def pool(self) -> Pool:
        """
        Returns the database connection pool used by the bot.

        :returns: The database connection pool.
        :rtype: :class:`asyncpg.pool.Pool`
        """

        return self.client.pool
