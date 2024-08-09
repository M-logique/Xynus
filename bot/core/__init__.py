from discord import Color as _Color
from discord import Object as _Object

from .client import Client
from .logger import Logger
from .settings import settings as _settings

color = _Color.from_rgb(*_settings.MAIN_COLOR)

