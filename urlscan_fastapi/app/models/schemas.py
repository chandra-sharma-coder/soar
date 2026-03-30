from pydantic import BaseModel, HttpUrl


class DetonateURLRequest(BaseModel):
    url: HttpUrl


class DetonateURLResponse(BaseModel):
    status: str
    message: str
    data: list
    summary: dict
    
    
class GetReportRequest(BaseModel):
    uuid: str


class LookupDomainRequest(BaseModel):
    domain: str