"""Keyed async token-bucket rate limiter with bounded LRU eviction for MCP JSON-RPC servers."""

from __future__ import annotations

import math
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

import anyio


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of a rate-limit admission check."""

    allowed: bool
    remaining: float
    retry_after_seconds: float
    bucket_key: str


@dataclass
class _BucketState:
    tokens: float
    last_refill: float


class TokenBucketRateLimiter:
    """Per-key token-bucket rate limiter with LRU memory bounding and anyio backpressure support.

    Suitable for throttling MCP tool invocations, resource reads, or client sessions
    without allowing unbounded cardinality attacks to exhaust server memory.
    """

    def __init__(
        self,
        rate_per_second: float,
        burst_capacity: float,
        *,
        max_buckets: int = 10_000,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if not math.isfinite(rate_per_second) or rate_per_second <= 0:
            raise ValueError("rate_per_second must be a positive finite number")
        if not math.isfinite(burst_capacity) or burst_capacity <= 0:
            raise ValueError("burst_capacity must be a positive finite number")
        if max_buckets < 1:
            raise ValueError("max_buckets must be >= 1")

        self.rate_per_second = float(rate_per_second)
        self.burst_capacity = float(burst_capacity)
        self.max_buckets = int(max_buckets)
        self._clock = clock if callable(clock) else time.monotonic
        self._buckets: OrderedDict[str, _BucketState] = OrderedDict()
        self._lock = anyio.Lock()
        self._allowed_total = 0
        self._rejected_total = 0
        self._evicted_buckets = 0

    def _refill_bucket(self, key: str, now: float) -> _BucketState:
        bucket = self._buckets.get(key)
        if bucket is None:
            if len(self._buckets) >= self.max_buckets:
                self._buckets.popitem(last=False)
                self._evicted_buckets += 1
            bucket = _BucketState(tokens=self.burst_capacity, last_refill=now)
            self._buckets[key] = bucket
            return bucket

        self._buckets.move_to_end(key)
        elapsed = max(0.0, now - bucket.last_refill)
        if elapsed > 0.0:
            bucket.tokens = min(
                self.burst_capacity,
                bucket.tokens + elapsed * self.rate_per_second,
            )
            bucket.last_refill = now
        return bucket

    def try_acquire(self, key: str = "default", cost: float = 1.0) -> RateLimitDecision:
        """Attempt immediate non-blocking token acquisition for a given bucket key."""
        if not isinstance(key, str) or not key.strip():
            key = "default"
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("cost must be a positive finite number")
        if cost > self.burst_capacity:
            self._rejected_total += 1
            return RateLimitDecision(
                allowed=False,
                remaining=0.0,
                retry_after_seconds=math.inf,
                bucket_key=key,
            )

        now = self._clock()
        bucket = self._refill_bucket(key, now)

        if bucket.tokens >= cost:
            bucket.tokens -= cost
            self._allowed_total += 1
            return RateLimitDecision(
                allowed=True,
                remaining=round(bucket.tokens, 4),
                retry_after_seconds=0.0,
                bucket_key=key,
            )

        deficit = cost - bucket.tokens
        retry_after = deficit / self.rate_per_second
        self._rejected_total += 1
        return RateLimitDecision(
            allowed=False,
            remaining=round(bucket.tokens, 4),
            retry_after_seconds=round(retry_after, 4),
            bucket_key=key,
        )

    async def acquire(
        self,
        key: str = "default",
        cost: float = 1.0,
        timeout: float | None = None,
    ) -> RateLimitDecision:
        """Asynchronously wait for tokens up to optional timeout seconds."""
        if timeout is not None and (not math.isfinite(timeout) or timeout < 0):
            raise ValueError("timeout must be a non-negative finite number or None")

        deadline = None if timeout is None else self._clock() + timeout

        while True:
            async with self._lock:
                decision = self.try_acquire(key=key, cost=cost)
            if decision.allowed:
                return decision
            if math.isinf(decision.retry_after_seconds):
                return decision

            wait_time = decision.retry_after_seconds
            if deadline is not None:
                remaining_budget = deadline - self._clock()
                if remaining_budget <= 0 or wait_time > remaining_budget:
                    return decision
                wait_time = min(wait_time, remaining_budget)

            await anyio.sleep(max(0.001, wait_time))

    def reset_key(self, key: str) -> bool:
        """Remove a single key's bucket state."""
        return self._buckets.pop(key, None) is not None

    def get_metrics(self) -> dict[str, int]:
        """Return operational telemetry counters for rate-limiter observability."""
        return {
            "allowed_total": self._allowed_total,
            "rejected_total": self._rejected_total,
            "active_buckets": len(self._buckets),
            "evicted_buckets": self._evicted_buckets,
        }
