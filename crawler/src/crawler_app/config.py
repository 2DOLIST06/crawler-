from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./crawler.db"
    app_secret_key: str = "change-me"
    admin_username: str = "admin"
    admin_password: str = "admin"
    default_user_agent: str = "crawler-app/1.0"
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
