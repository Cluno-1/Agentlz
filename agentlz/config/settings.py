import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
    MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    # 可扩展更多配置项

settings = Settings()