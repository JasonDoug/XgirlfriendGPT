import time
import threading
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status

class RateLimiter:
    """
    Sliding-window token bucket rate limiter to prevent API abuse, DDoS,
    and un-throttled visual / LLM generation requests.
    Thread-safe implementation protected by a reentrant lock.
    """
    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.client_tokens: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        with self._lock:
            now = time.time()
            fill_rate = self.requests_per_minute / 60.0

            if client_ip not in self.client_tokens:
                self.client_tokens[client_ip] = (now, float(self.burst_limit) - 1.0)
                return True

            last_update, tokens = self.client_tokens[client_ip]
            delta = now - last_update
            tokens = min(float(self.burst_limit), tokens + delta * fill_rate)

            if tokens >= 1.0:
                self.client_tokens[client_ip] = (now, tokens - 1.0)
                return True

            self.client_tokens[client_ip] = (now, tokens)
            return False

# Rate limiter instances for standard chat and heavy media generation endpoints
chat_rate_limiter = RateLimiter(requests_per_minute=60, burst_limit=15)
media_rate_limiter = RateLimiter(requests_per_minute=10, burst_limit=4)

def check_chat_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not chat_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another message."
        )

def check_media_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not media_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Media generation rate limit exceeded. Please wait a few seconds."
        )
