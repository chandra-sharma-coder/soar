"""
Lookup Domain Action
Handles domain search operations
"""
from typing import Dict, Any
from app.services.urlscan_service import UrlscanService


class LookupDomainAction:
    """
    Action class for domain lookups.
    Searches for scans related to a specific domain.
    """

    def __init__(self):
        """Initialize the action with URLscan service."""
        self.service = UrlscanService()

    def execute(self, domain: str) -> Dict[str, Any]:
        """
        Execute the domain lookup action.
        
        Args:
            domain: The domain to search for
            
        Returns:
            Dict containing status, message, data, and summary
        """
        result = self.service.lookup_domain(domain)

        if not result["success"]:
            return {
                "status": "failed",
                "message": result["error"],
                "data": [],
                "summary": {}
            }

        results = result.get("results", [])

        return {
            "status": "success",
            "message": f"Domain lookup successful: found {len(results)} results",
            "data": results,
            "summary": {
                "domain": domain,
                "result_count": len(results)
            }
        }