from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    # Use SettingsConfigDict for Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # This is the "Magic" line that fixes your error
    )

# Single instance shared across the whole app
settings = Settings() # type: ignore