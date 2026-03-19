from src.core.config.settings import settings
from redis import Redis
from rq import Queue

redis_connection = Redis.from_url(settings.redis_url)

extract_queue = Queue("extract_queue", connection=redis_connection)
upload_queue = Queue("upload_queue", connection=redis_connection)
match_queue = Queue("match_queue", connection=redis_connection)