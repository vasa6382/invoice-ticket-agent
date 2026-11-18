import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Enterprise Invoice & Ticket Automation Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Financial thresholds
    THRESHOLD_USD: float = 1000.0
    THRESHOLD_INR: float = 50000.0
    
    # Database
    DATABASE_PATH: str = os.path.join(os.path.dirname(__file__), "..", "invoices_audit.db")
    
    # Security
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: str = os.getenv("INVOICE_API_KEY", "powerautomate-secret-token-2026")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
