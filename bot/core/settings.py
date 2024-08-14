from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=False,
        extra="allow",
    )

    # Main Vars
    TOKEN: str
    OWNERS: List[ int ] = []
    MAIN_COLOR: List[int] = [47, 49, 54]
    PREFIX: List[str] = [","]
    STRIP_AFTER_PREFIX: Optional[bool] = True
    DEV_LOGS_CHANNEL: int

    DSN: Optional[str] = None

    DATABASE_NAME: Optional[str] = None

    HOST: Optional[str] = None
    PORT: Optional[int] = None
    
    USERNAME: Optional[str] = None
    PASSWORD: Optional[str] = None


settings = Settings()