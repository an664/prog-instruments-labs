from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from http import HTTPStatus
from typing import Dict, List, Optional

from tester import TestResult


@dataclass
class Summary:
    total_sent: int
    completed_successfully: int
    failed: int
    timeouts: int
    connection_errors: int
    http_errors: int
    status_counts: Dict[int, int]
    timings_ms: List[float]


@dataclass
class TimingStats:
    count: int
    min_ms: Optional[float]
    max_ms: Optional[float]
    mean_ms: Optional[float]
    median_ms: Optional[float]
    p75_ms: Optional[float]
    p90_ms: Optional[float]
    p95_ms: Optional[float]
    p99_ms: Optional[float]


def summarize_results(result: TestResult) -> Summary:
    status_counts: Dict[int, int] = {}
    timings_ms: List[float] = []
    connection_errors = 0
    http_errors = 0
    success = 0

    for item in result.results:
        if item.status is None:
            connection_errors += 1
            continue

        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        if item.elapsed_ms is not None:
            timings_ms.append(item.elapsed_ms)

        if item.status >= 500:
            http_errors += 1
        else:
            success += 1

    failed = result.timeouts + connection_errors + http_errors
    completed_successfully = max(result.total_sent - failed, 0)

    return Summary(
        total_sent=result.total_sent,
        completed_successfully=completed_successfully,
        failed=failed,
        timeouts=result.timeouts,
        connection_errors=connection_errors,
        http_errors=http_errors,
        status_counts=status_counts,
        timings_ms=timings_ms,
    )


def compute_timing_stats(timings_ms: List[float]) -> TimingStats:
    if not timings_ms:
        return TimingStats(
            count=0,
            min_ms=None,
            max_ms=None,
            mean_ms=None,
            median_ms=None,
            p75_ms=None,
            p90_ms=None,
            p95_ms=None,
            p99_ms=None,
        )

    timings_ms.sort()
    return TimingStats(
        count=len(timings_ms),
        min_ms=timings_ms[0],
        max_ms=timings_ms[-1],
        mean_ms=statistics.mean(timings_ms),
        median_ms=statistics.median(timings_ms),
        p75_ms=_percentile(timings_ms, 75),
        p90_ms=_percentile(timings_ms, 90),
        p95_ms=_percentile(timings_ms, 95),
        p99_ms=_percentile(timings_ms, 99),
    )


def format_report(
    url: str,
    rps: float,
    test_time: float,
    wait_timeout: float,
    summary: Summary,
    timings: TimingStats,
) -> str:
    lines: List[str] = [
        f"Target URL: {url}",
        (
            "Test duration: "
            f"{_format_seconds(test_time)}s, "
            f"RPS: {_format_number(rps)} "
            f"(total {summary.total_sent} requests)"
        ),
        f"Timeout for responses: {_format_seconds(wait_timeout)}s",
        "",
        "=== Request Summary ===",
        f"Total requests sent:    {summary.total_sent}",
        f"Completed successfully: {summary.completed_successfully}",
        f"Failed requests:        {summary.failed}",
        f"- Timeout errors:       {summary.timeouts}",
        f"- Connection errors:    {summary.connection_errors}",
        f"- HTTP errors (5xx):    {summary.http_errors}",
        "",
        "=== Response Time (ms) ===",
    ]

    if timings.count == 0:
        lines.append("No completed responses.")
    else:
        lines.extend(
            [
                f"Min:     {_format_ms(timings.min_ms)}",
                f"Max:     {_format_ms(timings.max_ms)}",
                f"Mean:    {_format_ms(timings.mean_ms)}",
                f"Median:  {_format_ms(timings.median_ms)}",
                f"p75:     {_format_ms(timings.p75_ms)}",
                f"p90:     {_format_ms(timings.p90_ms)}",
                f"p95:     {_format_ms(timings.p95_ms)}",
                f"p99:     {_format_ms(timings.p99_ms)}",
            ]
        )

    lines.append("")
    lines.append("=== Status Code Distribution ===")

    if summary.status_counts:
        for code in sorted(summary.status_counts):
            label = _status_label(code)
            lines.append(f"{code} {label}: {summary.status_counts[code]}")
    else:
        lines.append("No responses.")

    if summary.timeouts:
        lines.append(f"Timeouts: {summary.timeouts}")
    if summary.connection_errors:
        lines.append(f"Connection errors: {summary.connection_errors}")

    return "\n".join(lines)


def _percentile(values: List[float], percentile: float) -> float:
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * (percentile / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return values[low]
    weight = rank - low
    return values[low] + (values[high] - values[low]) * weight


def _format_seconds(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _format_ms(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def _status_label(code: int) -> str:
    try:
        return HTTPStatus(code).phrase
    except ValueError:
        return "Unknown"
