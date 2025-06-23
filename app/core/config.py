# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Loads and validates application settings from a .env file."""
    OPENAI_API_KEY: str
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# This line creates the 'settings' object that your other scripts can import.
settings = Settings()