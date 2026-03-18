import os
from rq import Worker
from src.data.clients.redis import redis_connection, extract_queue, upload_queue, match_queue

print("🚀 worker.py starting...")

try:
    pong = redis_connection.ping()
    print(f"✅ Redis connected — ping: {pong}")
except Exception as e:
    print(f"🔥 Redis connection FAILED: {e}")
    raise

queues = [extract_queue, upload_queue, match_queue]
print(f"✅ Starting worker for queues: {[q.name for q in queues]}")
worker = Worker(queues, connection=redis_connection)
print("✅ worker created, starting work loop...")
worker.work(with_scheduler=False)