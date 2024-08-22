from os import makedirs as _makedirs
from os import path

from asyncpg import Connection, connect
from discord import Activity as _Activity
from discord import ActivityType as _ActivityType
from discord import AllowedMentions as _AllowedMentions
from discord import Forbidden as _Forbidden
from discord import HTTPException as _HTTPException
from discord import Intents as _Intents
from discord import Status
from discord.ext import commands as _commands
from discord.ui import View as _View
from discord.utils import cached_property as _cached_property
from discord import Color as _Color
from discord import Message as _Message
from typing import Union as _Union

from .. import __name__ as name
from .. import __version__ as version
from ..templates.embeds import ErrorEmbed
from ..utils.database import KVDatabase
from ..utils.functions import list_all_dirs, search_directory
from .logger import Logger as _Logger
from .settings import settings
from ..templates.context import XynusContext
from typing import TypeVar, Type



DCT = TypeVar("DCT", bound="XynusContext")

# Custom context handling from:
#   https://github.com/DuckBot-Discord/duck-hideout-manager-bot/blob/main/utils/bot_bases/context.py


class Xynus(_commands.AutoShardedBot):
    

    def __init__(self, intents: _Intents, 
                allowed_mentions: _AllowedMentions,
                **options):


        owner_ids = settings.OWNERS
        prefix = settings.PREFIX
        
        super().__init__(
            command_prefix=_commands.when_mentioned_or(*prefix),
            owner_ids=owner_ids,
            strip_after_prefix=True,
            allowed_mentions=allowed_mentions, 
            intents=intents,
            **options
        )

        self.logger = _Logger(name)
        self.view_cache = set()
        self.context_class: _Union[XynusContext, _commands.Context] = _commands.Context
        

    async def on_ready(self):

        
        await self.change_presence(
            activity=_Activity(
                type=_ActivityType.watching, 
                name=f"?help - {name} V{version}"
            ),
            status=Status.idle
        )


        if self.cogs != {}: return self.logger.warn("Skipped loading extensions: Reconnecting")

        self.logger.success(f"Discord Client Logged in as {self.user.name}")

        # Extension loading stuff

        self.logger.info("Started loading Extensions")
    
        for dir in list_all_dirs("./extensions"):

            await self.load_extensions(dir)


        self.logger.info("Finished loading Extensions")
        try:
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} command(s).")
        except Exception as err:

            self.logger.error("Failed to sync command tree: {}".format(err))
    
    async def on_command_error(self, ctx: _commands.Context, error: _commands.CommandError):
        from ..templates.views import ViewWithDeleteButton
        if isinstance(error, _commands.CommandNotFound):
            return # type: ignore

        elif isinstance(error, _commands.MissingPermissions):
            text = "Sorry **{}**, you do not have permissions to do that!".format(ctx.message.author)
            
        elif isinstance(error, _commands.CommandOnCooldown):
            text = f'This command is on cooldown, you can use it in {round(error.retry_after, 2)}s.'

        elif isinstance(error, _commands.NotOwner):
            text = "This command is only for the owner."

        else: 
            err = str(error)

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
        formatted_kwargs = " ".join(f"{x}={y}" for x, y in kwargs.items())
        self.logger.error(
            f"Error in event {event_method}. Args: {args}. Kwargs: {formatted_kwargs}",
            exc_info=True,
        )



    async def load_extensions(self, path: str) -> None:
        for extension in search_directory(path):
            try:

                await self.load_extension(extension)
                self.logger.success("loaded {}".format(extension))
                
            except Exception as err:

                self.logger.error("There was an error loading {}, Error: {}".format(extension, err))

    def run(self):



        return super().run(
            settings.TOKEN,
            log_handler=self.logger.handler,
            log_formatter=self.logger.formatter,
            log_level=self.logger.level,
            root_logger=self.logger.root
        )
    


    async def get_context(
        self, message: _Message, *, cls: Type[DCT] | None = None
    ) -> _Union[XynusContext, _commands.Context["Xynus"]]:
        """|coro|

        Used to get the invocation context from the message.

        Parameters
        ----------
        message: :class:`~discord.Message`
            The message to get the prefix of.
        cls: Type[:class:`XynusContext`]
            The class to use for the context.
        """
        
        new_cls = cls or self.context_class
        return await super().get_context(message, cls=new_cls)

    async def setup_hook(self) -> None:
        if not path.exists("./data"):
            _makedirs("./data")
        try:
            self.pool: Connection = await connect(
                dsn=settings.DSN,
                host=settings.HOST,
                password=settings.PASSWORD,
                user=settings.USERNAME,
                database=settings.DATABASE_NAME,
                port=settings.PORT
            )

            self.db = KVDatabase(self.pool)
            await self.db._setup()
            
            setup_query = self._load_query("setup.sql")
            await self.pool.fetch(setup_query)

            self.logger.success("Connected to the database.")

        except Exception as err:

            self.logger.error(f"Failed to connect to the database {err}")

        from ..templates.views import PersistentViews

        view_collection = PersistentViews(self)
        view_collection.add_views()

        """|coro|

        Used to get the invocation context from the message.

        Parameters
        ----------
        message: :class:`~discord.Message`
            The message to get the prefix of.
        cls: Type[:class:`HideoutContext`]
            The class to use for the context.
        """

    def set_user_view(
            self,
            user_id: int,
            view: _View
    ) -> None:
        
        self.view_cache[user_id] = view

    def _load_query(
            self,
            name: str, 
            /
    ) -> str:
        """Load an SQL query from a file.

        Parameters:
        name (str): The name of the SQL file containing the query.

        Returns:
        str: The contents of the SQL file as a string.

        Raises:
        FileNotFoundError: If the file specified by `path` does not exist.
        IOError: If there is an error reading the file.
    
        """


        base_path = "./sql/"
        with open(base_path+name) as file:
            return file.read().strip()
        

    @_cached_property
    def color(self):
        """Retrives client's vanity color."""


        return _Color.from_rgb(*settings.MAIN_COLOR)