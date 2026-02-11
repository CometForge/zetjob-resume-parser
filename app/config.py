from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class GeminiConfig(BaseModel):
    provider: str = "google"
    model_flash: str = "gemini-2.5-flash"
    model_pro: str = "gemini-2.5-pro"
    api_key_env: str = "GEMINI_API_KEY"  # placeholder, no calls yet

class OcrConfig(BaseModel):
    provider: str = os.getenv("OCR_PROVIDER", "stub")
    api_key_env: str = os.getenv("OCR_API_KEY_ENV", "OCR_API_KEY")

class AntivirusConfig(BaseModel):
    provider: str = os.getenv("AV_PROVIDER", "stub")
    api_key_env: str = os.getenv("AV_API_KEY_ENV", "AV_API_KEY")

class AppConfig(BaseModel):
    env: str = os.getenv("APP_ENV", "dev")
    gemini: GeminiConfig = GeminiConfig()
    ocr: OcrConfig = OcrConfig()
    antivirus: AntivirusConfig = AntivirusConfig()

config = AppConfig()
