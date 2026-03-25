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
    payload: dict[str, Any] = {
        "status": status,
        "result": result,
        "error": error,
    }
    redis_connection.setex(f"job:{file_id}", 3600, json.dumps(payload, cls=SafeEncoder))


async def get_job_status(file_id: str) -> dict[str, Any] | None:
    raw = await async_redis.get(f"job:{file_id}")

    if not raw:
        return None

    try:
        return cast(dict[str, Any], json.loads(raw.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
