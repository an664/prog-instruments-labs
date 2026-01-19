from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from aiohttp import TCPConnector
from aiohttp.resolver import AsyncResolver

DEFAULT_HEADERS = {"Accept-Language": "ru-RU"}


@dataclass(frozen=True)
class TestConfig:
    url: str
    rps: float
    test_time: float
    wait_timeout: float
    method: str = "GET"
    max_connections: int = 0


@dataclass
class RequestResult:
    status: Optional[int]
    elapsed_ms: Optional[float]
    error: Optional[str] = None


@dataclass
class TestResult:
    total_sent: int
    results: List[RequestResult]
    timeouts: int


async def _fetch(session: aiohttp.ClientSession, config: TestConfig) -> RequestResult:
    start = time.perf_counter()
    try:
        async with session.request(
            config.method,
            config.url,
            headers=DEFAULT_HEADERS,
        ) as response:
            await response.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return RequestResult(status=response.status, elapsed_ms=elapsed_ms)
    except asyncio.CancelledError:
        raise
    except aiohttp.ClientError:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return RequestResult(status=None, elapsed_ms=elapsed_ms, error="connection")
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return RequestResult(status=None, elapsed_ms=elapsed_ms, error="connection")


async def run_load_test(config: TestConfig) -> TestResult:
    total_requests = int(config.rps * config.test_time)
    if total_requests <= 0:
        return TestResult(total_sent=0, results=[], timeouts=0)

    try:
        resolver = AsyncResolver()
    except Exception as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError(
            "Async DNS resolver requires 'aiodns'. Install requirements.txt."
        ) from exc

    connector = TCPConnector(limit=config.max_connections, resolver=resolver)
    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks: List[asyncio.Task[RequestResult]] = []
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        interval = 1.0 / config.rps

        for i in range(total_requests):
            scheduled = start_time + (i * interval)
            now = loop.time()
            if scheduled > now:
                await asyncio.sleep(scheduled - now)
            tasks.append(asyncio.create_task(_fetch(session, config)))

        done, pending = await asyncio.wait(tasks, timeout=config.wait_timeout)
        timeouts = len(pending)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        results: List[RequestResult] = []
        for task in done:
            try:
                results.append(task.result())
            except Exception:
                results.append(RequestResult(status=None, elapsed_ms=None, error="connection"))

    return TestResult(total_sent=total_requests, results=results, timeouts=timeouts)
