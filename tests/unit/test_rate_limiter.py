from types import SimpleNamespace

from app.core.rate_limiter import RateLimiterMiddleware, TokenBucket


def request(client_host: str, forwarded_for: str | None = None):
    headers = {"x-forwarded-for": forwarded_for} if forwarded_for else {}
    return SimpleNamespace(client=SimpleNamespace(host=client_host), headers=headers)


def test_forwarded_for_ignored_from_untrusted_client():
    limiter = RateLimiterMiddleware(app=lambda scope, receive, send: None, trusted_proxy_ips={"127.0.0.1"})
    assert limiter._get_client_key(request("203.0.113.8", "1.2.3.4")) == "203.0.113.8"


def test_forwarded_for_used_from_trusted_proxy():
    limiter = RateLimiterMiddleware(app=lambda scope, receive, send: None, trusted_proxy_ips={"127.0.0.1"})
    assert limiter._get_client_key(request("127.0.0.1", "1.2.3.4")) == "1.2.3.4"


def test_stale_buckets_are_evicted():
    limiter = RateLimiterMiddleware(app=lambda scope, receive, send: None, bucket_idle_ttl=60)
    stale = TokenBucket(10)
    stale.last_update -= 61
    limiter.buckets["stale"] = stale

    limiter._prune_buckets()

    assert "stale" not in limiter.buckets


def test_bucket_count_is_bounded_during_spoofing_burst():
    limiter = RateLimiterMiddleware(app=lambda scope, receive, send: None, max_client_buckets=2)

    limiter._get_or_create_bucket("client-1")
    limiter._get_or_create_bucket("client-2")
    limiter._get_or_create_bucket("client-3")

    assert len(limiter.buckets) <= 2
