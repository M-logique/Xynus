from typing import (Any, Callable, Dict, List, Optional, Sequence, Union,
                    overload)

from discord import (AllowedMentions, Embed, File, Forbidden, Interaction,
                     Message, MessageReference, PartialMessage)
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.context import MISSING
from discord.ext.commands.view import StringView
from discord.ui import View
from discord.utils import cached_property

from .views import ViewWithDeleteButton

# A large amount of code + ideas have been transferred from the HideoutManager project
#     https://github.com/DuckBot-Discord/duck-hideout-manager-bot/blob/main/utils/bot_bases/context.py


class XynusContext(commands.Context):

    def __init__(
            self, *, 
            message: Message, bot: Any, 
            view: StringView, args: List[Any] = ..., 
            kwargs: Dict[str, Any] = ..., prefix: str | None = None, 
            command: commands.Command[Any, Callable[..., Any], Any] | None = None, 
            invoked_with: str | None = None, 
            invoked_parents: List[str] = ..., 
            invoked_subcommand: commands.Command[Any, Callable[..., Any], Any] | None = None, 
            subcommand_passed: str | None = None, command_failed: bool = False, 
            current_parameter: commands.Parameter | None = None, 
            current_argument: str | None = None, 
            interaction: Interaction | None = None
    ):
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
    ) -> Message:
        ...

    async def send(self, content: str | None = None, **kwargs: Any) -> Message:
        """|coro|

        Sends a message to the invoking context's channel.

        View :meth:`~discord.ext.commands.Context.send` for more information of parameters.

        Returns
        -------
        :class:`~discord.Message`
            The message that was created.
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

        if kwargs.get('delete_button'):
            if kwargs.get('view'):
                raise TypeError("'view' and 'delete_button' cannot be passed together.")

            kwargs["view"] = ViewWithDeleteButton(self.author)

        try:
            return await super().send(content, **kwargs)
    
        except (Forbidden, HTTPException):
            pass # type: ignore


    @overload
    async def reply(  # type: ignore
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
    ) -> Message:
        ...

    async def reply(self, content: str | None = None, **kwargs: Any) -> Message:
        """|coro|

        A shortcut method to send to reply to the ~discord.Message referenced by this context..

        View :meth:`~discord.ext.commands.Context.send` for more information of parameters.

        Returns
        -------
        :class:`~discord.Message`
            The message that was created.
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

        if kwargs.get('delete_button'):
            if kwargs.get('view'):
                raise TypeError("'view' and 'delete_button' cannot be passed together.")

            kwargs["view"] = ViewWithDeleteButton(self.author)
        
        try:
            return await super().reply(content, **kwargs)
    
        except HTTPException as e:

            if e.response == 400: # ctx.message deleted before repling

                # Sending message instead of repling it
                return await self.send(content, **kwargs)
        
            self.bot.logger.warn(f"Whoops! Failed to reply the user {self.author.id} in channel {self.channel.id}: {e}")

        except Forbidden as e:
            self.bot.logger.warn(f"Whoops! Failed to reply the user {self.author.id} in channel {self.channel.id}: {e}")
            
    

    @cached_property
    def reference(self) -> Message | None:
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
        Load an SQL query from a file.
        """
        
        return self.bot._load_query(name)
    
    @property
    def created_at(self):
        return self.message.created_at

    @property
    def user(self):
        return self.author
    
    @property
    def channel_id(self):
        return self.channel.id