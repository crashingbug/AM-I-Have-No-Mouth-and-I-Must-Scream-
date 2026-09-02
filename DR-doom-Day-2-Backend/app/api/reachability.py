from fastapi import APIRouter
from app.schemas import DomainReachabilityRequest, DomainReachabilityResponse, MirrorAttemptModel
from app.services.domain_reachability import resolve_reachable_domain

router = APIRouter(prefix="/api/reachability", tags=["reachability"])


@router.post("/check", response_model=DomainReachabilityResponse)
async def check_domain_reachability(request: DomainReachabilityRequest) -> DomainReachabilityResponse:
    """
    Perform dynamic domain reachability health check and mirror fallback resolution.
    Pings primary domain and fallback mirrors using HTTP HEAD / GET with a 3s timeout.
    Returns the first verified active URL or an unreachable error.
    """
    result = resolve_reachable_domain(
        target=request.target,
        custom_mirrors=request.mirrors,
        timeout=request.timeout_seconds,
    )
    return DomainReachabilityResponse(
        target=result["target"],
        verifiedUrl=result["verified_url"],
        active=result["active"],
        checkedMirrors=[
            MirrorAttemptModel(
                url=m["url"],
                statusCode=m["status_code"],
                success=m["success"],
                error=m["error"],
            )
            for m in result["checked_mirrors"]
        ],
        message=result["message"],
    )
