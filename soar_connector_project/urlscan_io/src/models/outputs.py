# File: src/models/outputs.py
#
# Pydantic output models for each urlscan.io action.
# These replace the untyped ActionResult.add_data(dict) from the legacy connector.

from soar_sdk.action_results import ActionOutput, OutputField


class HuntOutput(ActionOutput):
    """Output for hunt_domain and hunt_ip — wraps the search API response."""

    results: list[dict] = OutputField(
        example_values=[],
    )
    total: int = OutputField(
        example_values=[0, 10, 100],
    )
    has_more: bool = OutputField(
        example_values=[True, False],
    )


class ReportOutput(ActionOutput):
    """Output for get_report — wraps the full scan result."""

    task: dict = OutputField(example_values=[{}])
    page: dict = OutputField(example_values=[{}])
    lists: dict = OutputField(example_values=[{}])
    stats: dict = OutputField(example_values=[{}])
    verdicts: dict = OutputField(example_values=[{}])


class ReportSummary(ActionOutput):
    """Summary for get_report."""

    added_tags_num: int


class DetonateUrlOutput(ActionOutput):
    """Output for detonate_url — wraps submission response and optional poll result."""

    uuid: str = OutputField(
        example_values=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    url: str = OutputField(
        cef_types=["url"],
        example_values=["https://example.com"],
    )
    visibility: str = OutputField(
        example_values=["public", "private"],
    )
    api_url: str = OutputField(
        example_values=["https://urlscan.io/api/v1/result/..."],
    )
    result_url: str = OutputField(
        example_values=["https://urlscan.io/result/..."],
    )
    scan_result: dict | None = None


class DetonateUrlSummary(ActionOutput):
    """Summary for detonate_url."""

    added_tags_num: int


class ScreenshotOutput(ActionOutput):
    """Output for get_screenshot."""

    vault_id: str = OutputField(
        example_values=["abc123"],
    )
    file_name: str = OutputField(
        example_values=["a1b2c3d4.png"],
    )
    container_id: int = OutputField(
        example_values=[1234],
    )
