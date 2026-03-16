# File: src/actions/hunt_domain.py
#
# Action handler: hunt domain — search urlscan.io for a domain.

from soar_sdk.logging import getLogger

from ..client import UrlscanClient
from ..models.outputs import HuntOutput
from ..models.params import HuntDomainParams

logger = getLogger()


def hunt_domain(params: HuntDomainParams, asset) -> HuntOutput:
    """Search urlscan.io for scans associated with a domain."""
    logger.debug(f"Searching urlscan.io for domain: {params.domain}")

    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)
    response = client.search_domain(params.domain)

    results = response.get("results", [])
    total = response.get("total", 0)
    has_more = response.get("has_more", False)

    if results:
        logger.info("Successfully retrieved information")
    else:
        logger.info("No data found")

    return HuntOutput(results=results, total=total, has_more=has_more)
