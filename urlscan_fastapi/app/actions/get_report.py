"""
Get Report Action
Handles retrieval of scan reports
"""
from typing import Dict, Any
from app.services.urlscan_service import UrlscanService


class GetReportAction:
    """
    Action class for retrieving scan reports.
    Fetches and formats scan report data.
    """

    def __init__(self):
        """Initialize the action with URLscan service."""
        self.service = UrlscanService()

    def execute(self, uuid: str) -> Dict[str, Any]:
        """
        Execute the get report action.
        
        Args:
            uuid: The scan UUID to retrieve
            
        Returns:
            Dict containing status, message, data, and summary
        """
        result = self.service.get_report(uuid)

        if not result["success"]:
            return {
                "status": "failed",
                "message": result["error"],
                "data": [],
                "summary": {}
            }

        return {
            "status": "success",
            "message": "Report fetched successfully",
            "data": [
                {
                    "uuid": uuid,
                    "url": result.get("url"),
                    "ip": result.get("ip"),
                    "country": result.get("country")
                }
            ],
            "summary": {
                "uuid": uuid,
                "url": result.get("url"),
                "ip": result.get("ip"),
                "country": result.get("country")
            }
        }