"""
Application Configuration
Centralized configuration management using environment variables
"""

import os


class Settings:
    """
    Application settings loaded from environment variables.

    Attributes:
        URLSCAN_API_KEY: API key for URLscan.io (optional for public scans)
        BASE_URL: Base URL for URLscan.io API
    """

    URLSCAN_API_KEY: str = os.getenv("URLSCAN_API_KEY", "")
    BASE_URL: str = "https://urlscan.io/api/v1"

    @property
    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self.URLSCAN_API_KEY)


# Global settings instance
settings = Settings()
