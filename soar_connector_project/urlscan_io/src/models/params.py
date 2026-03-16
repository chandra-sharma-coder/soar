# File: src/models/params.py
#
# Pydantic parameter models for each urlscan.io action.
# These replace the untyped `param` dicts from the legacy connector.

from soar_sdk.params import Param, Params


class HuntDomainParams(Params):
    domain: str = Param(
        description="Domain to search for in urlscan.io",
        primary=True,
        cef_types=["domain"],
    )


class HuntIpParams(Params):
    ip: str = Param(
        description="IP address to search for in urlscan.io",
        primary=True,
        cef_types=["ip"],
    )


class GetReportParams(Params):
    id: str = Param(
        description="UUID of the urlscan.io scan report to retrieve",
        primary=True,
        cef_types=["urlscan scan id"],
    )


class DetonateUrlParams(Params):
    url: str = Param(
        description="URL to submit for scanning on urlscan.io",
        primary=True,
        cef_types=["url"],
    )
    tags: str | None = Param(
        default=None,
        description="Comma-separated tags to attach to the scan (max 10)",
    )
    private: bool = Param(
        default=True,
        description="Whether to make the scan private",
    )
    custom_agent: str | None = Param(
        default=None,
        description="Custom user-agent string for the scan",
    )
    get_result: bool = Param(
        default=True,
        description="Whether to poll for and return scan results",
    )
    addto_vault: bool = Param(
        default=False,
        description="Whether to save the screenshot to vault",
    )


class GetScreenshotParams(Params):
    report_id: str = Param(
        description="UUID of the urlscan.io scan to get screenshot for",
        primary=True,
        cef_types=["urlscan scan id"],
    )
