from datetime import datetime as _datetime
from logging import getLogger
from os import makedirs as _makedirs
from os import path
from re import compile, escape, split
from time import time
from typing import TYPE_CHECKING, Any
from typing import Dict
from typing import Dict as _Dict
from typing import Optional as _Optional
from typing import Sequence, Tuple, Type, TypeVar
from typing import Union as _Union

from aiohttp import ClientSession
from asyncpg import Pool, create_pool
from discord import Activity as _Activity
from discord import ActivityType as _ActivityType
from discord import Color as _Color
from discord import Forbidden as _Forbidden
from discord import HTTPException as _HTTPException
from discord import Interaction, Status
from discord import utils as _utils
from discord.ext import commands as _commands
from discord.utils import cached_property as _cached_property

from .. import __version__ as version
from ..handlers.errorhandler import XynusExceptionManager
from ..templates.context import XynusContext
from ..templates.embeds import ErrorEmbed
from ..utils.database import KVDatabase
from ..utils.functions import (decrypt, find_command_args,
                               find_command_args_list, find_command_name,
                               list_all_dirs, match_and_remove_prefix,
                               search_directory)
from .logger import XynusLogger as _Logger
from .settings import settings

from string import Template

if TYPE_CHECKING:

    from discord import AllowedMentions as _AllowedMentions
    from discord import Intents as _Intents
    from discord import Message as _Message
    from discord.ui import View as _View
    




__all__: Tuple[str, ...] = (
    "Xynus"
)

XCT = TypeVar("XCT", bound="XynusContext")

# Custom context handling from:
#   https://github.com/DuckBot-Discord/duck-hideout-manager-bot/blob/main/utils/bot_bases/context.py


class Xynus(_commands.AutoShardedBot):
    """Custom implementation of an AutoShardedBot for Xynus."""


    __slots__: Tuple[str, ...] = (
        "error_webhook_url",
        "logger",
        "views",
        "context_class",
        "_start_time",
        "_cmd_mapping_cache",
        "db"
    )

    def __init__(
            self,
            intents: "_Intents", 
            allowed_mentions: "_AllowedMentions",
            args: Sequence[str],
            **options
        ) -> None:
        """
        Initializes the bot with the given parameters.

        :param intents: The intents to use for the bot.
        :type intents: :class:`discord.Intents`
        :param allowed_mentions: The allowed mentions settings for the bot.
        :type allowed_mentions: :class:`discord.AllowedMentions`
        :param options: Additional options to pass to the bot.
        :type options: dict
        """



        owner_ids = settings.OWNERS
        prefix = settings.PREFIX
        
        log_level = args.level or 20 # Defaults to logging.INFO

        self.logger = _Logger("xynus.main", level=log_level)

        self.views: _Dict[_View] = dict()
        self._cmd_mapping_cache: Dict[str, Any] = dict()
        

        self.error_webhook_url: _Optional[str] = settings.ERROR_WEBHOOK
        self._start_time: _Optional[_datetime] = None
        
        self._args = args
        self.context_class: _Union[XynusContext, _commands.Context] = XynusContext

        
        super().__init__(
            command_prefix=_commands.when_mentioned_or(*prefix),
            owner_ids=owner_ids,
            strip_after_prefix=True,
            allowed_mentions=allowed_mentions, 
            intents=intents,
            case_insensitive=True,
            **options,
        )

        

    async def on_ready(self):
        """
        Called when the bot is ready.

        This function changes the bot's presence, loads extensions, and syncs the command tree.
        """
        
        await self.change_presence(
            activity=_Activity(
                type=_ActivityType.watching, 
                name=f"?help - Xynus V{version}"
            ),
            status=Status.idle
        )

        log = getLogger("xynus.ext")

        if self.cogs != {}: return log.warn("Skipped loading extensions: Reconnecting")

        self.logger.info(f"Discord Client Logged in as {self.user.name}")

        # Extension loading stuff

        log.info("Started loading Extensions")
    
        for dir in list_all_dirs("./extensions"):
            await self.load_extensions(dir)


        log.info("Finished loading Extensions")


        try:
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} command(s).")
        except Exception as err:
            self.logger.error("Failed to sync command tree: {}".format(err))

        if not self._start_time:
            self._start_time = _utils.utcnow()
    
    async def on_command_error(self, ctx: "XynusContext", error: _commands.CommandError):
        """
        Handles errors raised during command invocation.

        :param ctx: The context in which the command was invoked.
        :type ctx: :class:`XynusContext`
        :param error: The exception that was raised.
        :type error: :class:`discord.ext.commands.CommandError`
        """




        from ..templates.views import ViewWithDeleteButton
        if isinstance(error, _commands.CommandNotFound):
            return # type: ignore

        elif isinstance(error, _commands.MissingPermissions):
            text = "Sorry **{}**, you do not have permissions to do that!".format(ctx.message.author)
            
        elif isinstance(error, _commands.CommandOnCooldown):
            text = f'This command is on cooldown, you can use it in {round(error.retry_after, 2)}s.'

        elif isinstance(error, _commands.NotOwner):
            text = "This command is only for the owner."
        
        elif isinstance(error, _commands.BadArgument):
            text = error.message

        else: 
            err = str(error)
            # await self.exceptions.add_error(error=error, ctx=ctx, log_error=False)

            text = err[:300:] # A Large error text is not good to display.

            if len(err) > 300:
                text += "..."
            
        embed = ErrorEmbed(text)
        view = ViewWithDeleteButton(ctx.author)

        try:
            view.message = await ctx.reply(
                embed=embed,
                view=view
            )

        except (_HTTPException, _Forbidden):
            pass # type: ignore
        
    async def on_error(self, event_method: str, /, *args, **kwargs):
        """
        Handles errors that occur during event processing.

        :param event_method: The name of the event method that caused the error.
        :type event_method: str
        :param args: The positional arguments that were passed to the event.
        :type args: tuple
        :param kwargs: The keyword arguments that were passed to the event.
        :type kwargs: dict
        """



        formatted_kwargs = " ".join(f"{x}={y}" for x, y in kwargs.items())
        self.logger.error(
            f"Error in event {event_method}. Args: {args}. Kwargs: {formatted_kwargs}",
            exc_info=True,
        )



    async def load_extensions(self, path: str) -> None:
        """|coro|

        Loads all extensions from a given directory path.

        :param path: The directory path containing extensions to load.
        :type path: str
        """



        for extension in search_directory(path):
            log = getLogger("xynus.ext")

            if any(extension.endswith(ignored) for ignored in self._args.ignore):
                log.info("Skipped loading Extension: {}".format(extension))
                continue


            try:
                await self.load_extension(extension)
                log.info("loaded {}".format(extension))
                
            except Exception as err:
                log.error("There was an error loading {}, Error: {}".format(extension, err))

    def run(self):
        """Runs the bot.

        This method starts the bot using the provided settings and logging configurations.
        """

        return super().run(
            settings.TOKEN,
            log_handler=self.logger.handler,
            log_formatter=self.logger.formatter,
            log_level=self.logger.level,
            root_logger=self.logger.root
        )
    


    async def get_context(
        self, message: "_Message", *, cls: Type[XCT] | None = None
    ) -> _Union[XynusContext, _commands.Context["XynusContext"]]:
        """
        |coro|

        Retrieves the invocation context for the given message, checking for cached command mappings.

        :param message: The message to get the context from, including its prefix and command.
        :type message: :class:`discord.Message`
        :param cls: The class to use for the context. Defaults to the bot's context class.
        :type cls: Type[:class:`XynusContext`], optional
        :return: The invocation context for the message.
        :rtype: :class:`XynusContext`
        """

        new_cls = cls or self.context_class
        if isinstance(message, Interaction):
            return await super().get_context(message, cls=new_cls)
        
        cached_mapping: Dict[str, Any] = self._cmd_mapping_cache.get(message.author.id, {})
        if not cached_mapping and message.guild:
            cached_mapping = self._cmd_mapping_cache.get(message.guild.id, {})


        prefixes = await self.get_prefix(message)

        if not prefixes:
            return await super().get_context(message, cls=new_cls)
        
        prefixless_content = match_and_remove_prefix(prefixes, message.content)
        
        if prefixless_content:
            command_name = find_command_name(prefixless_content)

            

            cached_command: _Optional[str] = cached_mapping.get(command_name, None)
            if cached_command:
                listed_args = find_command_args_list(
                    message.content, 
                    prefixes, 
                    command_name
                )

                args = find_command_args(
                    message.content,
                    prefixes,
                    command_name
                )

                kwargs = {
                    "args": args,
                }

                for i, arg in enumerate(listed_args):
                    kwargs[f"arg{i+1}"] = arg

                cached_command = Template(cached_command).safe_substitute(
                    **kwargs
                )

                message.content = prefixes[0]+cached_command
        
        

        return await super().get_context(message, cls=new_cls)
        

    async def setup_hook(self) -> None:
        """
        |coro|

        Initial setup tasks for the bot such as establishing 
        database connections and caching custom mappings.

        """


        if not path.exists("./data"):
            _makedirs("./data")
        
        self.session = ClientSession()
        
        self.exceptions: XynusExceptionManager = XynusExceptionManager(self)


        try:
            start_time = time()
            self.pool: Pool = await create_pool(
                dsn=settings.DSN,
                host=settings.HOST,
                password=settings.PASSWORD,
                user=settings.USERNAME,
                database=settings.DATABASE_NAME,
                port=settings.PORT
            )

            taked_time = round((time() - start_time) * 1000 , 3)

            self.db = KVDatabase(await self.pool.acquire())
            await self.db._setup()
            
            setup_query = self._load_query("setup.sql")
            await self.pool.execute(setup_query)

            

            log = getLogger("xynus.db")
            log.info(f"Connected to the database in {taked_time}ms")

            rcount = await self._update_mapping_cache()

            if rcount:
                log.info(f"Cached {rcount!r} custom command mapping.")

        except Exception as err:
            self.logger.error(f"Failed to connect to the database {err}")

        from ..templates.views import PersistentViews

        view_collection = PersistentViews(self)
        view_collection.add_views()

    def set_user_view(
            self,
            user_id: int,
            view: "_View"
    ) -> None:
        """
        Sets a specific view for a user.

        :param user_id: The ID of the user to associate with the view.
        :type user_id: int
        :param view: The view to be associated with the user.
        :type view: :class:`discord.ui.View`
        """

        
        self.views[user_id] = view

    def _load_query(
            self,
            name: str, 
            /
    ) -> str:
        """Load an SQL query from a file.

        :param name: The name of the SQL file containing the query.
        :type name: str
        :return: The SQL query as a string.
        :rtype: str
        """


        base_path = "./sql/"
        with open(base_path+name) as file:
            return file.read().strip()
        

    @_cached_property
    def color(self) -> _Color:
        """Retrives client's vanity color."""

        return _Color.from_rgb(*settings.MAIN_COLOR)
    

    async def _update_mapping_cache(self) -> int:
        """|coro|
        Updates mapping cache from the old data stored in database.

        :return: Cached records count.
        :rtype: int
        """
        query = """
        SELECT * FROM mappings;
        """

        records = await self.pool.fetch(query)
        for record in records:
            trigger = decrypt(record["trigger"])
            command = decrypt(record["command"])

            key = record["guild_id"] or record["user_id"]
            self.db._traverse_dict(
                self._cmd_mapping_cache,
                create_missing=True,
                keys=[key, trigger]
            )
            
            self._cmd_mapping_cache[key][trigger] = command

        return len(records)
