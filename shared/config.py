from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., env="TELEGRAM_TOKEN")
    SECRET_TOKEN: str = Field(..., env="TELEGRAM_SECRET_TOKEN")
    DOMAIN: str = Field("telegram.fisina.pt", env="DOMAIN")
    WEBHOOK_PORT: int = Field(8444, env="WEBAPP_PORT")
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PREFIX: str = Field("fsm", env="REDIS_PREFIX")

    @property
    def WEBHOOK_PATH(self) -> str:
        return f"/{self.BOT_TOKEN}"

    @property
    def WEBHOOK_URL(self) -> str:
        return f"https://{self.DOMAIN}{self.WEBHOOK_PATH}"

settings = Settings()
