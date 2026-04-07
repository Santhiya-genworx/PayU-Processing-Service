"""module: job_status.py"""

import json
from datetime import date, datetime
from typing import Any, cast

from src.data.clients.redis import async_redis, redis_connection


class SafeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def set_job_status(file_id: str, status: str, result: Any = None, error: Any = None) -> None:
    """Set the status of a job in Redis. This function takes a file ID, a status string, an optional result, and an optional error message as input. It constructs a payload containing the status, result, and error information, and stores it in Redis with an expiration time of 3600 seconds (1 hour). The payload is serialized to JSON using a custom encoder that can handle date and datetime objects. This function allows the application to track the status of background jobs and store relevant information for later retrieval."""
    payload: dict[str, Any] = {
        "status": status,
        "result": result,
        "error": error,
    }
    redis_connection.setex(f"job:{file_id}", 3600, json.dumps(payload, cls=SafeEncoder))


async def get_job_status(file_id: str) -> dict[str, Any] | None:
    """Retrieve the status of a job from Redis. This function takes a file ID as input, retrieves the corresponding job status from Redis, and returns it as a dictionary. If the job status is not found or if there is an error during retrieval, it returns None. The function handles any exceptions that may occur during the retrieval process and logs them for debugging purposes."""
    raw = await async_redis.get(f"job:{file_id}")

    if not raw:
        return None

    try:
        return cast(dict[str, Any], json.loads(raw.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
