"""
API Routes
Defines the HTTP endpoints for URLscan.io operations
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.actions.detonate_url import DetonateURLAction
from app.actions.get_report import GetReportAction
from app.actions.lookup_domain import LookupDomainAction
from app.models.schemas import (
    DetonateURLRequest,
    GetReportRequest,
    LookupDomainRequest
)

# Initialize API router
router = APIRouter()


@router.post("/detonate_url", response_model=Dict[str, Any])
async def detonate_url(request: DetonateURLRequest) -> Dict[str, Any]:
    """
    Submit a URL for scanning.
    
    Args:
        request: DetonateURLRequest containing the URL to scan
        
    Returns:
        Dict containing scan results with status, message, data, and summary
        
    Raises:
        HTTPException: If the scan submission fails
    """
    action = DetonateURLAction()
    result = action.execute(str(request.url))

    if result["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result


@router.post("/get_report", response_model=Dict[str, Any])
async def get_report(request: GetReportRequest) -> Dict[str, Any]:
    """
    Retrieve a scan report by UUID.
    
    Args:
        request: GetReportRequest containing the scan UUID
        
    Returns:
        Dict containing report data with status, message, data, and summary
        
    Raises:
        HTTPException: If the report retrieval fails
    """
    action = GetReportAction()
    result = action.execute(request.uuid)

    if result["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result


@router.post("/lookup_domain", response_model=Dict[str, Any])
async def lookup_domain(request: LookupDomainRequest) -> Dict[str, Any]:
    """
    Search for scans related to a domain.
    
    Args:
        request: LookupDomainRequest containing the domain to search
        
    Returns:
        Dict containing search results with status, message, data, and summary
        
    Raises:
        HTTPException: If the domain lookup fails
    """
    action = LookupDomainAction()
    result = action.execute(request.domain)

    if result["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result
