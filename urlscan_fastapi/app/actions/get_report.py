from app.services.urlscan_service import UrlscanService


class GetReportAction:

    def __init__(self):
        self.service = UrlscanService()

    def execute(self, uuid: str):
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
                    "url": result["url"],
                    "ip": result["ip"],
                    "country": result["country"]
                }
            ],
            "summary": {
                "url": result["url"],
                "ip": result["ip"]
            }
        }