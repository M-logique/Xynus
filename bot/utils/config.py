from typing import Any, Dict, Optional, Union


class Emojis:

    def __init__(self) -> None:
        from .functions import load_yaml


        self._config = load_yaml("./data/emojis.yml")
    
    def get(
            self,
            key: str, 
            /
    ) -> Union[None, Any]:

        return self._config.get(key)