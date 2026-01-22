from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    db_url: str = "postgresql+psycopg://postgres:changeme@127.0.0.1:5432/vsm_restaurant"
    payment_service_url: str = "http://payment-service:8001"
    payment_timeout_minutes: int = 15  # Таймаут оплаты
    cleanup_interval_minutes: int = 5   # Интервал очистки
    model_config = SettingsConfigDict(env_file="config.env")
