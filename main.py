from argparse import ArgumentParser

import discord
from discord import AllowedMentions, Intents

from bot.core import Xynus

parser = ArgumentParser()
parser.add_argument(
    "--ignore", "-I",
    nargs="+",
    default=[],
    help="A list of extension names to ignore during loading. Use space to separate multiple extensions (e.g., --ignore extensions.messages.smth)."
)
parser.add_argument(
    "--proxy", "-P", 
    nargs="?", 
    default=None, 
    help="The proxy server URL to use for network requests (e.g., --proxy http://proxyserver:port). If not specified, no proxy will be used."
)
parser.add_argument(
    "--level", "-L",
    nargs="?",
    type=lambda x: int(x) if x.isnumeric() else x.upper(), # Union[int, str]
    default=20,
    help="The log level for logger. can be int or str; defaults to INFO | 20."
)

args = parser.parse_args()

client = Xynus(
    intents=discord.Intents.all(),
    allowed_mentions=discord.AllowedMentions(replied_user=False),
    proxy=args.proxy,
    args=args
)


client.run()