import time
from fastapi import Request, status
from collections import defaultdict
import threading
from fastapi.responses import JSONResponse

class RateLimiter:
    """
    Thread-safe memory-based leaky bucket rate limiter.
    In production, this should be replaced with a Redis-backed solution.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.buckets = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        with self.lock:
            # Cleanup old requests
            self.buckets[key] = [t for t in self.buckets[key] if t > minute_ago]
            
            if len(self.buckets[key]) >= self.requests_per_minute:
                return False
            
            self.buckets[key].append(now)
            return True

# Initialize a global rate limiter
api_limiter = RateLimiter(requests_per_minute=100)

async def rate_limit_middleware(request: Request, call_next):
    # We apply rate limiting only to /v1/ routes
    if not request.url.path.startswith("/v1/"):
        return await call_next(request)

    # Use API key as bucket key, fallback to client IP when available.
    # Avoid eager default evaluation because request.client can be None (e.g., test transports).
    api_key = request.headers.get("X-API-Key")
    client_host = request.client.host if request.client else "unknown-client"
    key = api_key or client_host
    
    if not api_limiter.is_allowed(key):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Max 100 requests per minute."},
        )
        
    response = await call_next(request)
    return response
