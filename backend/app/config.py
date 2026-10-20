from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    assemblyai_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "mock"  # mock | openai | gemini
    frontend_origin: str = "http://localhost:5173"
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
