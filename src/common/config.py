# fraudshield/src/common/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_RAW_PAYMENTS_TOPIC: str
    KAFKA_PROCESSED_PAYMENTS_TOPIC: str
    KAFKA_FRAUD_ALERTS_TOPIC: str
    KAFKA_CONSUMER_GROUP_ID: str
    # Number of partitions to create for Kafka topics (used when creating topics on startup)
    # Keep reasonably small for local dev; increase in production to match consumer parallelism
    KAFKA_TOPIC_PARTITIONS: int = 3

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_KEY: str = "dev-secret-key"

settings = Settings()
