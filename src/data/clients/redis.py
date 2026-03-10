from src.core.config.settings import settings
from redis import Redis
from rq import Queue

redis_connection = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db
)

extract_queue = Queue("extract_queue", connection=redis_connection)
upload_queue = Queue("upload_queue", connection=redis_connection)