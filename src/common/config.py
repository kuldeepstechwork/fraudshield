# fraudshield/src/common/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # Configure Pydantic Settings to load from .env file
    # `extra='ignore'` allows other env vars to exist without Pydantic complaining
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://fraud_user:fraudpass@localhost/fraudshield_db"

    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_RAW_PAYMENTS_TOPIC: str = "raw_payments"
    KAFKA_PROCESSED_PAYMENTS_TOPIC: str = "processed_payments"
    KAFKA_FRAUD_ALERTS_TOPIC: str = "fraud_alerts"
    KAFKA_CONSUMER_GROUP_ID: str = "fraudshield_consumer_group"

    # Service specific settings (can be overridden for specific services in their Dockerfiles or env)
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

settings = Settings()