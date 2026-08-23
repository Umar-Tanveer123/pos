from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "POS System"
    API_V1_STR: str = "/api/v1"
    
    # Database settings - SQLite for local offline storage
    SQLITE_DB_NAME: str = "pos_system.db"

    # JWT Authentication
    SECRET_KEY: str = "super_secret_temporary_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days token for local POS

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return f"sqlite:///{os.path.join(base_dir, self.SQLITE_DB_NAME)}"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
