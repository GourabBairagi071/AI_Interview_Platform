from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    groq_api_key: str
    google_client_id: str

    # Razorpay (optional — payment features disabled when absent)
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Redis (optional — falls back to InMemoryEventPublisher if absent)
    redis_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()