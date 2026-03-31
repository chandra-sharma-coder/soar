"""
Urlscan Service Layer
Provides business logic for URLscan.io API operations
"""
from typing import Dict, Any
from app.clients.urlscan_client import UrlscanClient


class UrlscanService:
    """
    Service class for handling URLscan.io operations.
    Acts as an intermediary between actions and the API client.
    """

    def __init__(self):
        """Initialize the service with a URLscan client."""
        self.client = UrlscanClient()

    def detonate_url(self, url: str) -> Dict[str, Any]:
        """
        Submit a URL for scanning.

        Args:
            url: The URL to scan

        Returns:
            Dict containing success status, scan_id, and full response
        """
        success, result = self.client.submit_url(url)

        if not success:
            return {
                "success": False,
                "error": result
            }

        return {
            "success": True,
            "scan_id": result.get("uuid"),
            "full_response": result
        }

    def get_report(self, uuid: str) -> Dict[str, Any]:
        """
        Retrieve a scan report by UUID.

        Args:
            uuid: The scan UUID

        Returns:
            Dict containing success status and report data
        """
        success, result = self.client.get_report(uuid)

        if not success:
            return {"success": False, "error": result}

        return {
            "success": True,
            "url": result.get("task", {}).get("url"),
            "ip": result.get("page", {}).get("ip"),
            "country": result.get("page", {}).get("country"),
            "full_response": result
        }

    def lookup_domain(self, domain: str) -> Dict[str, Any]:
        """
        Search for scans related to a domain.

        Args:
            domain: The domain to search for

        Returns:
            Dict containing success status and search results
        """
        success, result = self.client.lookup_domain(domain)

        if not success:
            return {"success": False, "error": result}

        return {
            "success": True,
            "results": result.get("results", [])
        }
