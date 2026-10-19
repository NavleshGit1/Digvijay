from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DEMO_MODE: bool = True
    APP_SECRET_KEY: str = "airops-nexus-secret-key-at-least-32-characters-long"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "airops_nexus"
    POSTGRES_USER: str = "airops_user"
    POSTGRES_PASSWORD: str = "airops_secure_password"
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://airops_user:airops_secure_password@localhost:5432/airops_nexus"
    )

    # Redis & Broker
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "airops_minio_admin"
    MINIO_SECRET_KEY: str = "airops_minio_secure_key"
    MINIO_BUCKET_NAME: str = "airops-artifacts"
    MINIO_SECURE: bool = False

    # Security
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Virtual Clock Defaults
    DEFAULT_CLOCK_MODE: str = "system"
    DEFAULT_DEMO_AS_OF: str = "2026-10-19T12:00:00Z"

    # Demo credentials
    DEMO_PLANNER_USER: str = "planner@airops.local"
    DEMO_PLANNER_PASSWORD: str = "PlannerSecurePass2026!"
    DEMO_REVIEWER_USER: str = "reviewer@airops.local"
    DEMO_REVIEWER_PASSWORD: str = "ReviewerSecurePass2026!"
    DEMO_ANALYST_USER: str = "analyst@airops.local"
    DEMO_ANALYST_PASSWORD: str = "AnalystSecurePass2026!"
    DEMO_ADMIN_USER: str = "admin@airops.local"
    DEMO_ADMIN_PASSWORD: str = "AdminSecurePass2026!"


settings = Settings()
