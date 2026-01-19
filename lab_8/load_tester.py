from __future__ import annotations

import argparse
import asyncio
import sys

from metrics import compute_timing_stats, format_report, summarize_results
from tester import TestConfig, run_load_test


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a number") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Async load tester for a single URL."
    )
    parser.add_argument("url", help="Target URL to test.")
    parser.add_argument("rps", type=_positive_float, help="Requests per second.")
    parser.add_argument("test_time", type=_positive_float, help="Duration in seconds.")
    parser.add_argument(
        "wait_timeout",
        type=_positive_float,
        help="Seconds to wait for responses after test_time.",
    )
    parser.add_argument(
        "--method",
        choices=["GET", "HEAD"],
        default="GET",
        help="HTTP method to use.",
    )
    parser.add_argument(
        "--max-connections",
        type=int,
        default=0,
        help="Maximum simultaneous connections (0 = unlimited).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_connections < 0:
        print("max-connections must be >= 0", file=sys.stderr)
        return 2

    config = TestConfig(
        url=args.url,
        rps=args.rps,
        test_time=args.test_time,
        wait_timeout=args.wait_timeout,
        method=args.method,
        max_connections=args.max_connections,
    )

    try:
        result = asyncio.run(run_load_test(config))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    summary = summarize_results(result)
    timings = compute_timing_stats(summary.timings_ms)
    report = format_report(
        url=config.url,
        rps=config.rps,
        test_time=config.test_time,
        wait_timeout=config.wait_timeout,
        summary=summary,
        timings=timings,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
