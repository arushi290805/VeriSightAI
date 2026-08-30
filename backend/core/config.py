import os
import pydantic
from dotenv import load_dotenv

load_dotenv()

class Settings(pydantic.BaseModel):
    GEMINI_API_KEYS: str = os.getenv("GEMINI_API_KEYS", "")
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_PRICE_PER_1K_TOKENS: float = 0.00015 # Based on current pricing

settings = Settings()

def get_gemini_api_keys() -> list[str]:
    keys = settings.GEMINI_API_KEYS.split(",")
    return [k.strip() for k in keys if k.strip()]
