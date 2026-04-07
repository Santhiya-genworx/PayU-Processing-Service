"""Module: redis.py"""

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from rq import Queue

from src.config.settings import settings

redis_connection = SyncRedis.from_url(settings.redis_url)

async_redis = AsyncRedis.from_url(settings.redis_url)

extract_queue = Queue("extract_queue", connection=redis_connection)
upload_queue = Queue("upload_queue", connection=redis_connection)
match_queue = Queue("match_queue", connection=redis_connection)
