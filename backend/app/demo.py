"""Abuse controls and response caching for the anonymous showcase."""

import asyncio
import hashlib
import time
from collections import OrderedDict, defaultdict, deque
from datetime import date
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings

HCAPTCHA_VERIFY_URL = "https://api.hcaptcha.com/siteverify"


class DemoGuard:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def verify_request(self, client_ip: str, captcha_token: str) -> None:
        """Validate CAPTCHA when configured and enforce an hourly per-IP limit."""
        if settings.hcaptcha_secret:
            if not captcha_token:
                raise HTTPException(status_code=403, detail="Please complete the CAPTCHA")
            try:
                async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                    response = await client.post(
                        HCAPTCHA_VERIFY_URL,
                        data={
                            "secret": settings.hcaptcha_secret,
                            "response": captcha_token,
                            "remoteip": client_ip,
                            "sitekey": settings.hcaptcha_site_key,
                        },
                    )
                response.raise_for_status()
                valid = bool(response.json().get("success"))
            except (httpx.HTTPError, ValueError) as exc:
                raise HTTPException(
                    status_code=503,
                    detail="CAPTCHA verification is temporarily unavailable",
                ) from exc
            if not valid:
                raise HTTPException(status_code=403, detail="CAPTCHA verification failed")

        now = time.monotonic()
        cutoff = now - 3600
        async with self._lock:
            if len(self._requests) > 5_000:
                stale = [
                    address
                    for address, timestamps in self._requests.items()
                    if not timestamps or timestamps[-1] < cutoff
                ]
                for address in stale:
                    self._requests.pop(address, None)
                while len(self._requests) > 5_000:
                    self._requests.pop(next(iter(self._requests)))
            requests = self._requests[client_ip]
            while requests and requests[0] < cutoff:
                requests.popleft()
            if len(requests) >= settings.demo_queries_per_hour:
                raise HTTPException(
                    status_code=429,
                    detail="Hourly demo query limit reached. Please try again later.",
                    headers={"Retry-After": "3600"},
                )
            requests.append(now)

    async def reserve_generation(self) -> None:
        """Enforce a Qdrant-backed daily cap only for uncached LLM calls."""
        async with self._lock:
            from app.retrieval.search import reserve_demo_generation

            allowed = await asyncio.to_thread(
                reserve_demo_generation,
                date.today().isoformat(),
                settings.demo_queries_per_day,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="The demo has reached its daily generation limit. Try again tomorrow.",
                    headers={"Retry-After": "86400"},
                )

    @staticmethod
    def cache_key(question: str, top_k: int, doc_ids: list[str]) -> str:
        normalized = " ".join(question.lower().split())
        raw = f"{normalized}\0{top_k}\0{'|'.join(sorted(doc_ids))}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get_cached(self, key: str) -> dict[str, Any] | None:
        if settings.demo_cache_size == 0:
            return None
        async with self._lock:
            value = self._cache.get(key)
            if value is not None:
                self._cache.move_to_end(key)
                return dict(value)
        return None

    async def put_cached(self, key: str, response: dict[str, Any]) -> None:
        if settings.demo_cache_size == 0:
            return
        async with self._lock:
            self._cache[key] = dict(response)
            self._cache.move_to_end(key)
            while len(self._cache) > settings.demo_cache_size:
                self._cache.popitem(last=False)


demo_guard = DemoGuard()
