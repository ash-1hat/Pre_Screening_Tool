"""
Configuration settings for the FastAPI application
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    app_name: str = "Medical Pre-Screening API"
    debug: bool = True
    
    # Gemini Configuration
    gemini_api_key: str = Field(..., description="Gemini API key")
    gemini_model: str = "gemini-2.5-flash-lite"
    
    # Session Configuration
    session_timeout: int = 3600  # 1 hour in seconds
    
    # Hospital Data
    departments_csv_path: str = "DepartmentswithDoctors.csv"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

settings = Settings()
