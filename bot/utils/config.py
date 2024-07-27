from typing import Any, Optional, Dict, Union


class Emojis:

    def __init__(self) -> None:
        from .functions import load_yaml


        self._config = load_yaml("./data/emojis.yml")
        self.pagination: Optional[Dict] = self._config.get("pagination")
        self.global_emojis: Optional[Dict] = self._config.get("global")