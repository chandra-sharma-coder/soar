# File: src/client.py
#
# HTTP client for the urlscan.io REST API.
# Replaces the legacy _make_rest_call / _process_response methods.

import time

import httpx
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

logger = getLogger()

MAX_POLLING_ATTEMPTS = 10
POLLING_INTERVAL_SECONDS = 15
MAX_TAGS = 10
BASE_URL = "https://urlscan.io"


class UrlscanClient:
    """Typed HTTP client for urlscan.io API."""

    def __init__(self, api_key: str | None = None, timeout: int = 120):
        self._api_key = api_key
        self._timeout = timeout

    def _build_headers(self, include_json_content_type: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["API-Key"] = self._api_key
        if include_json_content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict | None = None,
        include_json_content_type: bool = False,
    ) -> httpx.Response:
        url = f"{BASE_URL}{endpoint}"
        headers = self._build_headers(include_json_content_type)

        with httpx.Client(timeout=self._timeout) as client:
            response = client.request(method, url, headers=headers, json=json_data)

        return response

    # ── Test Connectivity ──

    def test_connectivity(self) -> dict:
        """Validate API key / connectivity via GET /user/quotas/."""
        response = self._request("GET", "/user/quotas/")
        if not response.is_success:
            raise ActionFailure(
                f"Connectivity test failed: {response.status_code} - {response.text}"
            )
        return response.json()

    # ── Search (Hunt) ──

    def search_domain(self, domain: str) -> dict:
        """Search urlscan.io for a domain."""
        response = self._request("GET", f"/api/v1/search/?q=domain:{domain}")
        if not response.is_success:
            raise ActionFailure(
                f"Domain search failed: {response.status_code} - {response.text}"
            )
        return response.json()

    def search_ip(self, ip: str) -> dict:
        """Search urlscan.io for an IP address."""
        response = self._request("GET", f'/api/v1/search/?q=ip:"{ip}"')
        if not response.is_success:
            raise ActionFailure(
                f"IP search failed: {response.status_code} - {response.text}"
            )
        return response.json()

    # ── Scan Submission ──

    def submit_scan(
        self,
        url: str,
        private: bool = True,
        tags: list[str] | None = None,
        custom_agent: str | None = None,
    ) -> dict:
        """Submit a URL for scanning via POST /api/v1/scan/."""
        if not self._api_key:
            raise ActionFailure("API Key is required to submit a scan")

        if tags and len(tags) > MAX_TAGS:
            raise ActionFailure(
                f"Number of tags ({len(tags)}) exceeds maximum of {MAX_TAGS}"
            )

        data: dict = {
            "url": url,
            "public": "off" if private else "on",
            "tags": tags or [],
        }
        if custom_agent:
            data["customagent"] = custom_agent

        response = self._request(
            "POST",
            "/api/v1/scan/",
            json_data=data,
            include_json_content_type=True,
        )

        # 400 = bad request — return response data for the output, don't raise
        if response.status_code == 400:
            return response.json()

        if not response.is_success:
            raise ActionFailure(
                f"Scan submission failed: {response.status_code} - {response.text}"
            )

        return response.json()

    # ── Result Retrieval ──

    def get_result(self, uuid: str) -> dict:
        """Get scan result via GET /api/v1/result/{uuid}."""
        response = self._request("GET", f"/api/v1/result/{uuid}")
        if not response.is_success and response.status_code != 404:
            raise ActionFailure(
                f"Failed to get result: {response.status_code} - {response.text}"
            )
        return response.json()

    def poll_for_result(self, uuid: str) -> dict | None:
        """Poll for scan result with retries.

        Returns the scan result dict, or None if the scan did not complete
        within the maximum number of polling attempts.
        """
        for attempt in range(1, MAX_POLLING_ATTEMPTS + 1):
            logger.progress(f"Polling attempt {attempt} of {MAX_POLLING_ATTEMPTS}")

            result = self.get_result(uuid)

            # Still pending — 404 or explicit "notdone"
            status = result.get("status", 0)
            if status == 404 or result.get("message") == "notdone":
                time.sleep(POLLING_INTERVAL_SECONDS)
                continue

            # Bad request — real error
            if status == 400:
                raise ActionFailure(
                    f"Scan failed: {result.get('message', 'Unknown error')}"
                )

            return result

        return None

    # ── Screenshot ──

    def get_screenshot(self, uuid: str) -> bytes:
        """Download screenshot PNG via GET /screenshots/{uuid}.png."""
        response = self._request("GET", f"/screenshots/{uuid}.png")
        if not response.is_success:
            raise ActionFailure(f"Screenshot download failed: {response.status_code}")
        return response.content
