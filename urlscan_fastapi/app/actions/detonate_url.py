from app.services.urlscan_service import UrlscanService


class DetonateURLAction:

    def __init__(self):
        self.service = UrlscanService()

    def execute(self, url: str):
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
            "message": "URL submitted successfully",
            "data": [
                {
                    "scan_id": scan_id
                }
            ],
            "summary": {
                "scan_id": scan_id
            }
        }