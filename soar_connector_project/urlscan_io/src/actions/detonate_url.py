# File: src/actions/detonate_url.py
#
# Action handler: detonate url — submit URL for scanning, optionally poll for results
# and save screenshot to vault.

from soar_sdk.abstract import SOARClient
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from ..client import UrlscanClient
from ..models.outputs import DetonateUrlOutput, DetonateUrlSummary
from ..models.params import DetonateUrlParams

logger = getLogger()


def detonate_url(
    params: DetonateUrlParams, asset, soar: SOARClient[DetonateUrlSummary]
) -> DetonateUrlOutput:
    """Submit a URL for scanning on urlscan.io and optionally poll for results."""
    logger.debug(f"Detonating URL: {params.url}")

    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)

    # Parse and validate tags
    tags: list[str] = []
    if params.tags:
        tags = [t.strip() for t in params.tags.split(",")]
        tags = list(set(filter(None, tags)))

    # Submit the scan
    response = client.submit_scan(
        url=params.url,
        private=params.private,
        tags=tags,
        custom_agent=params.custom_agent,
    )

    # Check for bad request (400) — the legacy connector returned this as success with message
    if response.get("status") == 400:
        msg = response.get("message", "None")
        desc = response.get("description", "None")
        logger.info(f"Bad request: {msg}. Description: {desc}")
        return DetonateUrlOutput(
            uuid="",
            url=params.url,
            visibility="private" if params.private else "public",
            api_url="",
            result_url="",
            scan_result=response,
        )

    report_uuid = response.get("uuid")
    if not report_uuid:
        raise ActionFailure("Unable to get report UUID from scan")

    scan_result: dict | None = None

    # Poll for results if requested
    if params.get_result or params.addto_vault:
        result = client.poll_for_result(report_uuid)
        if result is not None and params.get_result:
            scan_result = result
            task = result.get("task", {})
            soar.set_summary(
                DetonateUrlSummary(added_tags_num=len(task.get("tags", [])))
            )

    # Save screenshot to vault if requested
    if params.addto_vault:
        try:
            screenshot_bytes = client.get_screenshot(report_uuid)
            container_id = soar.get_executing_container_id()
            soar.vault.create_attachment(
                container_id=container_id,
                file_content=screenshot_bytes,
                file_name=f"{report_uuid}.png",
                metadata={"source": "urlscan.io", "scan_uuid": report_uuid},
            )
            logger.info(f"Screenshot saved to vault for container {container_id}")
        except Exception as e:
            raise ActionFailure(f"Failed to save screenshot to vault: {e}")

    soar.set_message("Successfully retrieved information")

    return DetonateUrlOutput(
        uuid=report_uuid,
        url=params.url,
        visibility="private" if params.private else "public",
        api_url=response.get("api", ""),
        result_url=response.get("result", ""),
        scan_result=scan_result,
    )
