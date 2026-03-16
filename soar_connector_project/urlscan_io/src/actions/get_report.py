# File: src/actions/get_report.py
#
# Action handler: get report — retrieve scan results by UUID with polling.

from soar_sdk.abstract import SOARClient
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from ..client import UrlscanClient
from ..models.outputs import ReportOutput, ReportSummary
from ..models.params import GetReportParams

logger = getLogger()


def get_report(
    params: GetReportParams, asset, soar: SOARClient[ReportSummary]
) -> ReportOutput:
    """Retrieve a urlscan.io scan report by UUID, polling until ready."""
    logger.debug(f"Getting report for UUID: {params.id}")

    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)
    result = client.poll_for_result(params.id)

    if result is None:
        raise ActionFailure(f"Report not found, report uuid: {params.id}")

    task = result.get("task", {})
    tags = task.get("tags", [])

    soar.set_summary(ReportSummary(added_tags_num=len(tags)))
    soar.set_message("Successfully retrieved information")

    return ReportOutput(
        task=task,
        page=result.get("page", {}),
        lists=result.get("lists", {}),
        stats=result.get("stats", {}),
        verdicts=result.get("verdicts", {}),
    )
