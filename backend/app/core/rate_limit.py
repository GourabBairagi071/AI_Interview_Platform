import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """
    Sliding-window in-memory rate limiter.
    Provides IP-based or key-based rate limiting to mitigate brute-force and flood attacks.
    """

    def __init__(self, requests_per_minute: int = 60, cleanup_interval_seconds: int = 300):
        self.rpm = requests_per_minute
        self.cleanup_interval = cleanup_interval_seconds
        self.history = defaultdict(list)
        self.lock = Lock()
        self.last_cleanup = time.monotonic()

    def _cleanup_stale(self, now: float):
        if now - self.last_cleanup > self.cleanup_interval:
            cutoff = now - 60.0
            stale_keys = [k for k, timestamps in self.history.items() if not timestamps or timestamps[-1] < cutoff]
            for k in stale_keys:
                del self.history[k]
            self.last_cleanup = now

    def check(self, key: str, max_requests: int | None = None) -> bool:
        max_req = max_requests or self.rpm
        now = time.monotonic()
        cutoff = now - 60.0

        with self.lock:
            self._cleanup_stale(now)
            timestamps = self.history[key]
            # Prune timestamps older than 60s
            valid = [ts for ts in timestamps if ts > cutoff]
            if len(valid) >= max_req:
                self.history[key] = valid
                return False
            valid.append(now)
            self.history[key] = valid
            return True


# Global instances for key domains
login_rate_limiter = InMemoryRateLimiter(requests_per_minute=30)
api_rate_limiter = InMemoryRateLimiter(requests_per_minute=300)


def limit_login_attempts(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    # Allow localhost / loopback high quota for local tests
    if client_ip in ("127.0.0.1", "localhost", "::1"):
        max_attempts = 150
    else:
        max_attempts = 20

    if not login_rate_limiter.check(f"login:{client_ip}", max_requests=max_attempts):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait a minute and try again.",
        )
