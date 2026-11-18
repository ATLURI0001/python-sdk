import math
import pytest

from mcp.shared.rate_limiter import TokenBucketRateLimiter


def test_token_bucket_burst_refill_and_retry_after():
    now = [100.0]
    limiter = TokenBucketRateLimiter(rate_per_second=2.0, burst_capacity=3.0, clock=lambda: now[0])

    # Consume full burst of 3
    d1 = limiter.try_acquire("client-a", cost=1.0)
    d2 = limiter.try_acquire("client-a", cost=1.0)
    d3 = limiter.try_acquire("client-a", cost=1.0)
    assert d1.allowed and d2.allowed and d3.allowed
    assert d3.remaining == 0.0

    # 4th immediate call must fail with exact 0.5s retry_after (1 token / 2 req/s)
    d4 = limiter.try_acquire("client-a", cost=1.0)
    assert d4.allowed is False
    assert d4.retry_after_seconds == 0.5

    # Advance 0.5s -> exactly 1 token refilled
    now[0] = 100.5
    d5 = limiter.try_acquire("client-a", cost=1.0)
    assert d5.allowed is True
    assert d5.remaining == 0.0

    # Cost exceeding burst capacity is rejected with infinite retry_after
    impossible = limiter.try_acquire("client-a", cost=5.0)
    assert impossible.allowed is False
    assert math.isinf(impossible.retry_after_seconds)


def test_token_bucket_lru_eviction_bounds_memory():
    now = [0.0]
    limiter = TokenBucketRateLimiter(rate_per_second=1.0, burst_capacity=2.0, max_buckets=2, clock=lambda: now[0])

    limiter.try_acquire("k1")
    limiter.try_acquire("k2")
    # Touch k1 so k2 becomes LRU
    limiter.try_acquire("k1")
    # Inserting k3 must evict k2
    limiter.try_acquire("k3")

    metrics = limiter.get_metrics()
    assert metrics["active_buckets"] == 2
    assert metrics["evicted_buckets"] == 1
    assert limiter.reset_key("k1") is True
    assert limiter.reset_key("k2") is False


@pytest.mark.anyio
async def test_async_acquire_backpressure_and_timeout():
    limiter = TokenBucketRateLimiter(rate_per_second=50.0, burst_capacity=1.0)
    first = await limiter.acquire("tool:search", cost=1.0)
    assert first.allowed is True

    # Very tight timeout (0.001s < 0.02s refill time) rejects immediately without hanging
    timed_out = await limiter.acquire("tool:search", cost=1.0, timeout=0.001)
    assert timed_out.allowed is False

    # Sufficient timeout waits and succeeds once refilled
    second = await limiter.acquire("tool:search", cost=1.0, timeout=0.5)
    assert second.allowed is True
