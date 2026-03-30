"""Rate limiting dependencies for API v1."""

from app.core.container import container
from app.domain.services.services import RateLimitService
from fastapi import Depends, HTTPException, Request, status


def get_rate_limiter_service() -> RateLimitService:
    """Resolve RateLimitService singleton from DI container."""
    return container.resolve(RateLimitService)


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request headers.

    Priority:
    1. X-Forwarded-For (first IP = original client)
    2. X-Real-IP (set by nginx)
    3. request.client.host (direct connection)

    Returns:
        Client IP address string
    """
    # Check X-Forwarded-For header (standard for load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the list is the original client
        # Format: "client, proxy1, proxy2, ..."
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # Check X-Real-IP header (set by nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


async def check_rate_limit(
    request: Request,
    rate_limiter: RateLimitService = Depends(get_rate_limiter_service),
) -> bool:
    """Check rate limit for incoming request.

    Returns:
        True if request is allowed
    """
    client_ip = get_client_ip(request)
    key = f"api:{client_ip}"

    if not await rate_limiter.is_allowed(key):
        remaining = await rate_limiter.get_remaining(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={
                "X-RateLimit-Limit": str(rate_limiter.limit),
                "X-RateLimit-Remaining": str(remaining),
                "Retry-After": "60",
            },
        )

    return True
