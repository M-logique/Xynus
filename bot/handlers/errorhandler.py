from asyncio import Lock, sleep
from datetime import datetime, timedelta
from logging import getLogger
from os import getcwd
from traceback import format_exception
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Tuple

from discord import Embed, Interaction, Webhook, utils

from ..templates.exceptions import (XynusException, XynusTraceback,
                                    XynusTracebackOptional)

if TYPE_CHECKING:
    from ..core import Xynus
    from ..templates.context import XynusContext

log = getLogger("xynus.errors")

# ErrorHandler from HideoutManager

class XynusExceptionManager:
    """A simple exception handler that sends all exceptions to a error
    Webhook and then logs them to the console.

    This class handles cooldowns with a simple lock, so you dont have to worry about
    rate limiting your webhook and getting banned :).

    .. note::

        If some code is raising MANY errors VERY fast and you're not there to fix it,
        this will take care of things for you.

    Attributes
    ----------
    bot: :class:`Xynus`
        The bot instance.
    cooldown: :class:`datetime.timedelta`
        The cooldown between sending errors. This defaults to 5 seconds.
    errors: Dict[str, Dict[str, Any]]
        A mapping of tracbacks to their error information.
    code_blocker: :class:`str`
        The code blocker used to format Discord codeblocks.
    error_webhook: :class:`discord.Webhook`
        The error webhook used to send errors.
    """

    __slots__: Tuple[str, ...] = ('bot', 'cooldown', '_lock', '_most_recent', 'errors', 'code_blocker', 'error_webhook')

    def __init__(self, bot: "Xynus", *, cooldown: timedelta = timedelta(seconds=5)) -> None:


        if not bot.error_webhook_url:
            raise XynusException('No error webhokk set in .env!')

        self.bot: Xynus = bot
        self.cooldown: timedelta = cooldown

        self._lock: Lock = Lock()
        self._most_recent: Optional[datetime] = None

        self.errors: Dict[str, List[XynusTraceback]] = {}
        self.code_blocker: str = '```py\n{}```'
        self.error_webhook: Webhook = Webhook.from_url(
            bot.error_webhook_url, session=bot.session, bot_token=bot.http.token
        )

    def _yield_code_chunks(self, iterable: str, *, chunksize: int = 2000) -> Generator[str, None, None]:
        cbs = len(self.code_blocker) - 2  # code blocker size

        for i in range(0, len(iterable), chunksize - cbs):
            yield self.code_blocker.format(iterable[i : i + chunksize - cbs])

    async def release_error(self, traceback: str, packet: XynusTraceback, log_error: bool = True) -> None:
        """|coro|

        Releases an error to the webhook and logs it to the console. It is not recommended
        to call this yourself, call :meth:`add_error` instead.

        Parameters
        ----------
        traceback: :class:`str`
            The traceback of the error.
        packet: :class:`dict`
            The additional information about the error.
        """
        if log_error:
            log.error('Releasing error to log', exc_info=packet['exception'])

        if self.error_webhook.is_partial():
            self.error_webhook = await self.error_webhook.fetch()

        fmt = {
            'time': utils.format_dt(packet['time']),
        }
        if author := packet.get('author'):
            fmt['author'] = f'<@{author}>'

        # This is a bit of a hack,  but I do it here so guild_id
        # can be optional, and I wont get type errors.
        # No chai it gets mad...
        guild_id = packet.get('guild')
        guild = self.bot.get_guild(guild_id or 0)
        if guild:
            fmt['guild'] = f'{guild.name} ({guild.id})'
        else:
            log.warning('Ignoring error packet with unknown guild id %s', guild_id)

        if guild:
            channel_id = packet.get('channel')
            if channel_id and (channel := guild.get_channel(channel_id)):
                fmt['channel'] = f'{channel.name} - {channel.mention} - ({channel.id})'

            # Let's try and upgrade the author
            author_id = packet.get('author')
            if author_id:
                author = guild.get_member(author_id) or self.bot.get_user(author_id)
                if author:
                    fmt['author'] = f'{str(author)} - {author.mention} ({author.id})'

        if not fmt.get('author') and (author_id := packet.get('author')):
            fmt['author'] = f'<Unknown User> - <@{author_id}> ({author_id})'

        if command := packet.get('command'):
            fmt['command'] = command.qualified_name
            display = f'in command "{command.qualified_name}"'
        else:
            display = f'in no command (in HideoutManager)'

        embed = Embed(title=f'An error has occured in {display}', timestamp=packet['time'])
        embed.add_field(
            name='Metadata',
            value='\n'.join([f'**{k.title()}**: {v}' for k, v in fmt.items()]),
        )

        kwargs: Dict[str, Any] = {}
        if self.bot.user:
            kwargs['username'] = self.bot.user.display_name
            kwargs['avatar_url'] = self.bot.user.display_avatar.url

            embed.set_author(name=str(self.bot.user), icon_url=self.bot.user.display_avatar.url)

        webhook = self.error_webhook
        if webhook.is_partial():
            self.error_webhook = webhook = await self.error_webhook.fetch()

        code_chunks = list(self._yield_code_chunks(traceback))

        embed.description = code_chunks.pop(0)
        await webhook.send(embed=embed, **kwargs)

        embeds: List[Embed] = []
        for entry in code_chunks:
            embed = Embed(description=entry)
            if self.bot.user:
                embed.set_author(name=str(self.bot.user), icon_url=self.bot.user.display_avatar.url)

            embeds.append(embed)

            if len(embeds) == 10:
                await webhook.send(embeds=embeds, **kwargs)
                embeds = []

        if embeds:
            await webhook.send(embeds=embeds, **kwargs)

    async def add_error(
        self, *, error: Exception, ctx: Optional["XynusContext" | Interaction["Xynus"]] = None, log_error: bool = True
    ) -> None:
        """|coro|

        Add an error to the error manager. This will handle all cooldowns and internal cache management
        for you. This is the recommended way to add errors.

        Parameters
        ----------
        error: :class:`Exception`
            The error to add.
        ctx: Optional[:class:`XynusContext`]
            The invocation context of the error, if any.
        """
        log.info('Adding error "%s" to log.', str(error))

        packet: XynusTraceback = {'time': (ctx and ctx.created_at) or utils.utcnow(), 'exception': error}

        if ctx is not None:
            addons: XynusTracebackOptional = {
                'command': ctx.command,
                'author': ctx.user.id,
                'guild': (ctx.guild and ctx.guild.id) or None,
                'channel': ctx.channel_id or 0,
            }
            packet.update(addons)

        traceback_string = ''.join(format_exception(type(error), error, error.__traceback__)).replace(
            getcwd(), 'CWD'
        )
        current = self.errors.get(traceback_string)

        if current:
            self.errors[traceback_string].append(packet)
        else:
            self.errors[traceback_string] = [packet]

        async with self._lock:
            # I want all other errors to be released after this one, which is why
            # lock is here. If you have code that calls MANY errors VERY fast,
            # this will ratelimit the webhook. We dont want that lmfao.

            if not self._most_recent:
                self._most_recent = utils.utcnow()
                await self.release_error(traceback_string, packet, log_error)
            else:
                time_between = packet['time'] - self._most_recent

                if time_between > self.cooldown:
                    self._most_recent = utils.utcnow()
                    return await self.release_error(traceback_string, packet, log_error)
                else:  # We have to wait
                    log.debug('Waiting %s seconds to release error', time_between.total_seconds())
                    await sleep(time_between.total_seconds())

                    self._most_recent = utils.utcnow()
                    return await self.release_error(traceback_string, packet, log_error)