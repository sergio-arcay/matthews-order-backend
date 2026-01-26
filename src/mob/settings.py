from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment or .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    is_docker_container: bool = Field(
        default=False,
        description="Indicates if the application is running inside a Docker container.",
    )
    api_config_path: Path = Field(
        default=Path(__file__).resolve().parents[2] / "api_config.json",
        description="Absolute path to the api_config.json file.",
    )
    default_timeout: float = Field(
        default=15.0,
        gt=0,
        description="Fallback timeout (in seconds) when an action omits it.",
    )
    log_level: str = Field(
        default="INFO",
        description="Python logging level."
    )
    discord_bot_token: str = Field(
        default="",
        description="Discord bot token used for connecting to the Discord API.",
    )
    gemini_api_key: str = Field(
        default="",
        description="API key for accessing Gemini models.",
    )
    openai_api_key: str = Field(
        default="",
        description="API key for accessing OpenAI models.",
    )
    open_router_api_key: str = Field(
        default="",
        description="API key for accessing OpenRouter models.",
    )
    g4f_api_base_url: str = Field(
        default="",
        description="Base URL for the G4F API endpoint.",
    )
    g4f_api_key: str = Field(
        default="",
        description="API key for accessing G4F models.",
    )
