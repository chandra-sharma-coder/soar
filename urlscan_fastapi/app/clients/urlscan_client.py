import requests
from app.core.config import settings


class UrlscanClient:

    def __init__(self):
        self.base_url = settings.BASE_URL
        self.api_key = settings.URLSCAN_API_KEY

    def submit_url(self, url: str):
        endpoint = f"{self.base_url}/scan/"
        headers = {}

        if self.api_key:
            headers["API-Key"] = self.api_key

        try:
            response = requests.post(
                endpoint,
                json={"url": url},
                headers=headers,
                timeout=10
            )

            if response.status_code not in [200, 201]:
                return False, f"HTTP {response.status_code}: {response.text}"

            return True, response.json()

        except requests.exceptions.RequestException as e:
            return False, str(e)