# File: src/actions/hunt_ip.py
#
# Action handler: hunt ip — search urlscan.io for an IP address.

from soar_sdk.logging import getLogger

from ..client import UrlscanClient
from ..models.outputs import HuntOutput
from ..models.params import HuntIpParams

logger = getLogger()


def hunt_ip(params: HuntIpParams, asset) -> HuntOutput:
    """Search urlscan.io for scans associated with an IP address."""
    logger.debug(f"Searching urlscan.io for IP: {params.ip}")

    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)
    response = client.search_ip(params.ip)

    results = response.get("results", [])
    total = response.get("total", 0)
    has_more = response.get("has_more", False)

    if results:
        logger.info("Successfully retrieved information")
    else:
        logger.info("No data found")

    return HuntOutput(results=results, total=total, has_more=has_more)
