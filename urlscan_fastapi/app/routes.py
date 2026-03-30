from app.actions.detonate_url import DetonateURLAction
from app.actions.get_report import GetReportAction
from app.actions.lookup_domain import LookupDomainAction
from app.models.schemas import DetonateURLRequest, GetReportRequest, LookupDomainRequest
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/detonate_url")
def detonate_url(request: DetonateURLRequest):
    action = DetonateURLAction()
    result = action.execute(request.url)

    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/get_report")
def get_report(request: GetReportRequest):
    action = GetReportAction()
    result = action.execute(request.uuid)

    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/lookup_domain")
def lookup_domain(request: LookupDomainRequest):
    action = LookupDomainAction()
    result = action.execute(request.domain)

    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["message"])

    return result
