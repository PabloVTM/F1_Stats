from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Fréquence (en requêtes) du balayage des IPs inactives
_SWEEP_EVERY = 100


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = {}
        self._since_sweep = 0

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Derrière un reverse proxy de confiance (Traefik/WAF), l'IP réelle
        # est dans X-Forwarded-For (première entrée).
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _sweep(self, now: float) -> None:
        cutoff = now - self.window_seconds
        inactive = [
            ip
            for ip, ts in self._store.items()
            if not ts or ts[-1] <= cutoff
        ]
        for ip in inactive:
            del self._store[ip]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.monotonic()

        self._since_sweep += 1
        if self._since_sweep >= _SWEEP_EVERY:
            self._since_sweep = 0
            self._sweep(now)

        cutoff = now - self.window_seconds
        timestamps = [t for t in self._store.get(ip, []) if t > cutoff]

        if len(timestamps) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"err": "rate_limit", "msg": "Trop de requêtes, réessaie dans quelques secondes"},
            )

        timestamps.append(now)
        self._store[ip] = timestamps
        return await call_next(request)
