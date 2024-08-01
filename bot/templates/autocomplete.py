from discord import app_commands, Interaction
from discord.ext import commands
from ..utils.functions import get_all_commands

async def help_autocomplete(
        inter: Interaction,
        current: str,
):
    def check_aliases(
            cmd: commands.Command,
    ):
        if cmd.aliases:
            for alias in cmd.aliases:
                if current in alias: return True
        
        return False
    
    bot_commands = []

    for cog_name in inter.client.cogs:
        cog = inter.client.cogs[cog_name]

        bot_commands+=get_all_commands(cog)

    full_name = lambda command: "{}{}{}".format(
        f"{command.root_parent} " if command.root_parent else "",
        f"{command.parent} " if command.parent and command.parent != command.root_parent else "",
        command.name,
    )

    choices = [
        app_commands.Choice(
            name=full_name(cmd),
            value=full_name(cmd)
        )
        for cmd in [*filter(lambda cmd: current.lower() in cmd.name or check_aliases(cmd), bot_commands)]
    ]

    return choices