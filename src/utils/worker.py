from rq import Worker

from src.data.clients.redis import (
    extract_queue,
    match_queue,
    redis_connection,
    upload_queue,
)
from src.observability.logging.logging_config import logger

logger.info("worker starting...")

try:
    pong = redis_connection.ping()
    logger.info(f"Redis connected — ping: {pong}")
except Exception as e:
    logger.error(f"Redis connection FAILED: {e}")
    raise

queues = [extract_queue, upload_queue, match_queue]
logger.info(f"Starting worker for queues: {[q.name for q in queues]}")
worker = Worker(queues, connection=redis_connection)
logger.info("worker created, starting work loop...")
worker.work(with_scheduler=False)
