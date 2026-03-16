# File: src/actions/get_screenshot.py
#
# Action handler: get screenshot — download scan screenshot and save to vault.

from soar_sdk.abstract import SOARClient
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from ..client import UrlscanClient
from ..models.outputs import ScreenshotOutput
from ..models.params import GetScreenshotParams

logger = getLogger()


def get_screenshot(
    params: GetScreenshotParams, asset, soar: SOARClient
) -> ScreenshotOutput:
    """Download a screenshot from urlscan.io and save it to the vault."""
    logger.debug(f"Getting screenshot for report: {params.report_id}")

    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)

    screenshot_bytes = client.get_screenshot(params.report_id)

    container_id = soar.get_executing_container_id()
    file_name = f"{params.report_id}.png"

    vault_id = soar.vault.create_attachment(
        container_id=container_id,
        file_content=screenshot_bytes,
        file_name=file_name,
        metadata={"source": "urlscan.io", "scan_uuid": params.report_id},
    )

    logger.info(f"Screenshot downloaded successfully in container: {container_id}")

    return ScreenshotOutput(
        vault_id=vault_id,
        file_name=file_name,
        container_id=container_id,
    )
