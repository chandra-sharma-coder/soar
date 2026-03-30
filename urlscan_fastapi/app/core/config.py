import os


class Settings:
    URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY", "")
    BASE_URL = "https://urlscan.io/api/v1"


settings = Settings()
