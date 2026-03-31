"""
Pydantic Models for Request/Response Validation
Defines the data schemas for API endpoints
"""
from typing import List, Dict, Any
from pydantic import BaseModel, HttpUrl, Field


class DetonateURLRequest(BaseModel):
    """Request model for URL detonation/scanning."""
    url: HttpUrl = Field(..., description="The URL to scan")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }


class DetonateURLResponse(BaseModel):
    """Response model for URL detonation."""
    status: str = Field(..., description="Status of the operation (success/failed)")
    message: str = Field(..., description="Human-readable message")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Response data")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary information")


class GetReportRequest(BaseModel):
    """Request model for retrieving a scan report."""
    uuid: str = Field(..., description="The scan UUID to retrieve")

    class Config:
        json_schema_extra = {
            "example": {
                "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }


class LookupDomainRequest(BaseModel):
    """Request model for domain lookup."""
    domain: str = Field(..., description="The domain to search for")

    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com"
            }
        }