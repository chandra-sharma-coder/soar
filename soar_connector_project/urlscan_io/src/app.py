# File: src/app.py
#
# Main module for the urlscan.io SOAR SDK connector.
# This is the entry point referenced by pyproject.toml [tool.soar.app] main_module.

import httpx
from soar_sdk.app import App
from soar_sdk.asset import AssetField, BaseAsset
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from .client import UrlscanClient

logger = getLogger()


# ── Asset Configuration ──


class Asset(BaseAsset):
    api_key: str | None = AssetField(
        default=None,
        sensitive=True,
        description="API key for urlscan.io (required for scan and search actions)",
    )
    timeout: int = AssetField(
        default=120,
        description="HTTP request timeout in seconds",
    )


# ── App Instance ──


app = App(
    asset_cls=Asset,
    name="urlscan_io",
    appid="c46c00cd-7231-4dd3-8d8e-02b9fa0e14a2",
    app_type="sandbox",
    product_vendor="urlscan GmbH",
    logo="logo.svg",
    logo_dark="logo_dark.svg",
    product_name="urlscan.io",
    publisher="Splunk Inc.",
    min_phantom_version="7.0.0",
    fips_compliant=True,
)


# ── Test Connectivity ──


@app.test_connectivity()
def test_connectivity(asset: Asset) -> None:
    """Verify connectivity and optionally validate API key against urlscan.io."""
    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)

    if asset.api_key:
        logger.info("Validating API Key")
    else:
        logger.info("No API key found, checking connectivity to urlscan.io")

    client.test_connectivity()
    logger.info("Test Connectivity Passed")


# ── Action Registrations ──
# Actions are defined in separate modules under src/actions/ and registered here.


app.register_action(
    "actions.hunt_domain:hunt_domain",
    action_type="investigate",
    identifier="hunt_domain",
    name="hunt domain",
    description="Search for a domain on urlscan.io",
    verbose="Search urlscan.io for scans associated with a domain.",
    read_only=True,
)

app.register_action(
    "actions.hunt_ip:hunt_ip",
    action_type="investigate",
    identifier="hunt_ip",
    name="hunt ip",
    description="Search for an IP on urlscan.io",
    verbose="Search urlscan.io for scans associated with an IP address.",
    read_only=True,
)

app.register_action(
    "actions.get_report:get_report",
    action_type="investigate",
    identifier="get_report",
    name="get report",
    description="Get the results of an existing urlscan.io scan",
    verbose="Retrieve a urlscan.io scan report by UUID, polling until results are ready.",
    read_only=True,
)

app.register_action(
    "actions.detonate_url:detonate_url",
    action_type="generic",
    identifier="detonate_url",
    name="detonate url",
    description="Submit a URL for scanning on urlscan.io",
    verbose="Submit a URL for scanning, optionally poll for results and save screenshot to vault.",
    read_only=False,
)

app.register_action(
    "actions.get_screenshot:get_screenshot",
    action_type="investigate",
    identifier="get_screenshot",
    name="get screenshot",
    description="Get the screenshot of an existing urlscan.io scan result",
    verbose="Download a screenshot from urlscan.io and save it to the SOAR vault.",
    read_only=True,
)


# ── CLI Entry Point ──


if __name__ == "__main__":
    app.cli()
