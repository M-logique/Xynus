from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=False)

    # Main Vars
    TOKEN: str
    OWNERS: List[ int ] = []
    MAIN_COLOR: List[int] = [47, 49, 54]
    PREFIX: List[str] = [","]
    STRIP_AFTER_PREFIX: Optional[bool] = True
    GUILDS: List[int] = []
    DB_BACKUP_CHANNEL: int

settings = Settings()