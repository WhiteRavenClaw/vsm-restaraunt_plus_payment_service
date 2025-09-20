from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str = "postgresql+psycopg://postgres:changeme@127.0.0.1:5432/vsm_restaurant"
    model_config = SettingsConfigDict(env_file="config.env")
