from app.clients.urlscan_client import UrlscanClient


class UrlscanService:

    def __init__(self):
        self.client = UrlscanClient()

    def detonate_url(self, url: str):
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
        
    def get_report(self, uuid: str):
        endpoint = f"{self.base_url}/result/{uuid}"

    try:
        response = requests.get(endpoint, timeout=10)

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text}"

        return True, response.json()

    except requests.exceptions.RequestException as e:
        return False, str(e)


    def lookup_domain(self, domain: str):
        endpoint = f"{self.base_url}/search/?q=domain:{domain}"

        try:
            response = requests.get(endpoint, timeout=10)

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text}"

            return True, response.json()

        except requests.exceptions.RequestException as e:
            return False, str(e)