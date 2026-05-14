from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./crawler.db"
    exports_dir: str = "exports"
    app_secret_key: str = "change-me"
    admin_username: str | None = None
    admin_password: str | None = None
    default_user_agent: str = "crawler-app/1.0"
    environment: str = "development"

    @model_validator(mode="after")
    def set_dev_admin_defaults(self) -> "Settings":
        if self.environment.lower() == "development":
            if not self.admin_username:
                self.admin_username = "admin"
            if not self.admin_password:
                self.admin_password = "admin"
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
