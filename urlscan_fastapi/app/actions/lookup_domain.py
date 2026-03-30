
from app.services.urlscan_service import UrlscanService


class LookupDomainAction:

    def __init__(self):
        self.service = UrlscanService()

    def execute(self, domain: str):
        result = self.service.lookup_domain(domain)

        if not result["success"]:
            return {
                "status": "failed",
                "message": result["error"],
                "data": [],
                "summary": {}
            }

        return {
            "status": "success",
            "message": "Domain lookup successful",
            "data": result["results"],
            "summary": {
                "result_count": len(result["results"])
            }
        }