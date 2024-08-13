from os import makedirs as _makedirs
from os import path

from discord import Activity as _Activity
from discord import ActivityType as _ActivityType
from discord import AllowedMentions as _AllowedMentions
from discord import Forbidden as _Forbidden
from discord import HTTPException as _HTTPException
from discord import Intents as _Intents
from discord import Status
from discord.ext import commands as _commands
from discord.ui import View as _View

from .. import __name__ as name
from .. import __version__ as version
from ..templates.embeds import ErrorEmbed
from ..utils.database import Database
from ..utils.functions import list_all_dirs, search_directory
from .logger import Logger as _Logger
from .settings import settings


class Client(_commands.Bot):


    def __init__(self, intents: _Intents, 
                allowed_mentions: _AllowedMentions,
                **options):

        self.logger = _Logger(name)


        owner_ids = settings.OWNERS
        prefix = settings.PREFIX
        strip_aftre_prefix = settings.STRIP_AFTER_PREFIX

        self.view_cache = {}

        super().__init__(
            command_prefix=_commands.when_mentioned_or(*prefix),
            owner_ids=owner_ids,
            strip_after_prefix=strip_aftre_prefix,
            allowed_mentions=allowed_mentions, 
            intents=intents,
            help_command=None,
            **options
        )

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
            pass

        elif isinstance(error, _commands.MissingPermissions):
            text = "Sorry **{}**, you do not have permissions to do that!".format(ctx.message.author)
            
        elif isinstance(error, _commands.CommandOnCooldown):
            text = f'This command is on cooldown, you can use it in {round(error.retry_after, 2)}s.'

        elif isinstance(error, _commands.NotOwner):
            text = "This command is only for the owner."

        else: 
            err = str(error)

            text = err[:300:]

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
            pass
        
        



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
    
    async def setup_hook(self) -> None:
        if not path.exists("./data"):
            _makedirs("./data")
        
        self.db = Database("./data/DataBase.db", ["main", "guilds"])
        from ..templates.views import PersistentViews

        view_collection = PersistentViews(self)
        view_collection.add_views()

    def set_user_view(
            self,
            user_id: int,
            view: _View
    ) -> None:
        
        self.view_cache[user_id] = view

    