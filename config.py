from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_USERNAME: str
    ADMIN_ID: int
    
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "polly"
    DB_USER: str = "postgres"
    DB_PASSWORD: str
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    YOOMONEY_TOKEN: str
    WEBHOOK_URL: str
    
    class Config:
        env_file = ".env"

settings = Settings()