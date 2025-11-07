import os

class Settings:
    DEEPSEEK_API_KEY = "sk-190a71f802514ea7bcc536df94e8292d"
    MODEL_NAME = "deepseek:deepseek-chat"
    MODEL_BASE_URL = "https://api.deepseek.com"
    OPENAI_API_KEY = "sk-190a71f802514ea7bcc536df94e8292d"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    # 可扩展更多配置项

settings = Settings()
