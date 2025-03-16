from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "JBox"
    API_PREFIX: str = ""
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "YOUR_SECRET_KEY_HERE")  # Should be changed in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database settings
    DATABASE_USER: str = os.getenv("DATABASE_USER")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT", "5432")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")
    DATABASE_URL: str = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    
    # Discord settings
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
    
    # File settings
    CHUNK_SIZE: int = 24 * 1024 * 1024  # 24MB
    
    class Config:
        case_sensitive = True

# Create a global settings object
settings = Settings()