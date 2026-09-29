from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: str
    jwt_issuer: str = "dummyjson-sync"
    jwt_access_token_minutes: int = 30
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    dummyjson_base_url: str = "https://dummyjson.com"
    dummyjson_timeout_seconds: int = 20
    sync_page_size: int = 100
    sync_interval_seconds: int = 1800
    log_level: str = "INFO"

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32 or value == "REPLACE_WITH_A_LONG_RANDOM_SECRET":
            raise ValueError("JWT_SECRET must be a unique random value of at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_bootstrap_admin(self):
        if bool(self.bootstrap_admin_username) != bool(self.bootstrap_admin_password):
            raise ValueError("Set both bootstrap admin username and password, or leave both empty")
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            raise ValueError("Bootstrap admin password must be at least 12 characters")
        return self

settings = Settings()

