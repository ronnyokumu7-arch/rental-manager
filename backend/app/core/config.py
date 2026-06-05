from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Rental Manager API"
    environment: str = "development"
    debug: bool = False
    SECRET_KEY: str
    access_token_expire_minutes: int = 60
    superadmin_password: str = "changeme"
    database_url: str = "postgresql://postgres:rentalpass@localhost:5432/rental_manager"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()