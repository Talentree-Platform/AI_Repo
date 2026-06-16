import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "Enterprise Recommendation System"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # SQL Server Database Settings (defaults match the live MonsterASP deployment)
    DB_USER: str = Field(default="db52715")
    DB_PASSWORD: str = Field(default="Kg4+5#hGcH=8")
    DB_HOST: str = Field(default="db52715.public.databaseasp.net")
    DB_PORT: str = Field(default="1433")
    DB_NAME: str = Field(default="db52715")
    
    # MLflow Settings
    MLFLOW_TRACKING_URI: str = Field(default="http://localhost:5000")
    
    # Model Directories
    MODEL_DIR: str = Field(default="./trained_models")
    FEATURE_STORE_DIR: str = Field(default="./data/processed")

    # JWT Authentication — must match the ASP.NET Talentree main API config
    JWT_SECRET_KEY: str = Field(default="CHANGE_ME_SET_IN_RAILWAY_ENV")
    JWT_ALGORITHM:  str = Field(default="HS256")
    JWT_ISSUER:     str = Field(default="TalentreeApi")
    JWT_AUDIENCE:   str = Field(default="TalentreeClient")

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def database_url(self) -> str:
        # We use pymssql driver which works beautifully out-of-the-box in Linux/Docker without ODBC driver headaches.
        return f"mssql+pymssql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
