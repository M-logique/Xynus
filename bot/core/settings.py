from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
    )

    # Main Vars
    TOKEN: str
    OWNERS: List[ int ] = []
    MAIN_COLOR: List[int] = [47, 49, 54]
    PREFIX: List[str] = [","]
    STRIP_AFTER_PREFIX: Optional[bool] = True
    DEV_LOGS_CHANNEL: int

settings = Settings()