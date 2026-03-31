"""
URLscan.io API Client
Handles direct communication with the URLscan.io API
"""
from typing import Tuple, Any
import requests
from app.core.config import settings


class UrlscanClient:
    """
    Client class for URLscan.io API.
    Handles HTTP requests to the URLscan.io API endpoints.
    """

    def __init__(self):
        """Initialize the client with API configuration."""
        self.base_url = settings.BASE_URL
        self.api_key = settings.URLSCAN_API_KEY

    def submit_url(self, url: str) -> Tuple[bool, Any]:
        """
        Submit a URL to URLscan.io for scanning.

        Args:
            url: The URL to scan

        Returns:
            Tuple of (success: bool, result: dict or error message)
        """
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

    def get_report(self, uuid: str) -> Tuple[bool, Any]:
        """
        Retrieve a scan report by UUID.

        Args:
            uuid: The scan UUID

        Returns:
            Tuple of (success: bool, result: dict or error message)
        """
        endpoint = f"{self.base_url}/result/{uuid}"

        try:
            response = requests.get(endpoint, timeout=10)

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text}"

            return True, response.json()

        except requests.exceptions.RequestException as e:
            return False, str(e)

    def lookup_domain(self, domain: str) -> Tuple[bool, Any]:
        """
        Search for scans related to a domain.

        Args:
            domain: The domain to search for

        Returns:
            Tuple of (success: bool, result: dict or error message)
        """
        endpoint = f"{self.base_url}/search/?q=domain:{domain}"

        try:
            response = requests.get(endpoint, timeout=10)

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text}"

            return True, response.json()

        except requests.exceptions.RequestException as e:
            return False, str(e)