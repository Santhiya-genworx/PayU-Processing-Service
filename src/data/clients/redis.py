# redis.py
from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from rq import Queue

from src.core.config.settings import settings

# Sync client for RQ workers
redis_connection = SyncRedis.from_url(settings.redis_url)

# Async client for job status get/set
async_redis = AsyncRedis.from_url(settings.redis_url)

extract_queue = Queue("extract_queue", connection=redis_connection)
upload_queue = Queue("upload_queue", connection=redis_connection)
match_queue = Queue("match_queue", connection=redis_connection)