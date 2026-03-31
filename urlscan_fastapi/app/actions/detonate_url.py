"""
Detonate URL Action
Handles URL submission for scanning
"""
from typing import Dict, Any
from app.services.urlscan_service import UrlscanService


class DetonateURLAction:
    """
    Action class for detonating (scanning) URLs.
    Coordinates the URL submission process and formats the response.
    """

    def __init__(self):
        """Initialize the action with URLscan service."""
        self.service = UrlscanService()

    def execute(self, url: str) -> Dict[str, Any]:
        """
        Execute the URL detonation action.
        
        Args:
            url: The URL to scan
            
        Returns:
            Dict containing status, message, data, and summary
        """
        result = self.service.detonate_url(url)

        if not result["success"]:
            return {
                "status": "failed",
                "message": result["error"],
                "data": [],
                "summary": {}
            }

        scan_id = result["scan_id"]

        return {
            "status": "success",
            "message": "URL submitted successfully for scanning",
            "data": [
                {
                    "scan_id": scan_id,
                    "url": url
                }
            ],
            "summary": {
                "scan_id": scan_id,
                "submitted_url": url
            }
        }