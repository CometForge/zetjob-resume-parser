from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class GeminiConfig(BaseModel):
    provider: str = "google"
    model_flash: str = "gemini-2.5-flash"
    model_pro: str = "gemini-2.5-pro"
    api_key_env: str = "GEMINI_API_KEY"  # placeholder, no calls yet

class AppConfig(BaseModel):
    env: str = os.getenv("APP_ENV", "dev")
    gemini: GeminiConfig = GeminiConfig()

config = AppConfig()
