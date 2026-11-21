import redis

from app.core.config import settings

_redis_client: redis.Redis | None = None
_redis_url_cached: str | None = None


def _resolve_redis_url() -> str:
    from app.services.integration_config import get_redis_url

    url = (get_redis_url() or "").strip()
    return url or settings.REDIS_URL


def reset_redis_client() -> None:
    global _redis_client, _redis_url_cached
    _redis_client = None
    _redis_url_cached = None


def get_redis() -> redis.Redis:
    global _redis_client, _redis_url_cached
    url = _resolve_redis_url()
    if _redis_client is None or _redis_url_cached != url:
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_url_cached = url
    return _redis_client
