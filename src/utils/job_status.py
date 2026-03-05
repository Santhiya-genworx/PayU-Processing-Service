import json
from datetime import date, datetime
from src.data.clients.redis import redis_connection


class SafeEncoder(json.JSONEncoder):
    """Handle date/datetime and other non-serializable types."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()  # "2024-01-15"
        return super().default(obj)


def set_job_status(file_id: str, status: str, result=None, error=None):
    """Save job status + result to Redis. Expires in 1 hour."""
    payload = {
        "status": status,
        "result": result,
        "error": error,
    }
    redis_connection.setex(
        f"job:{file_id}",
        3600,
        json.dumps(payload, cls=SafeEncoder)  # use safe encoder
    )


def get_job_status(file_id: str) -> dict | None:
    """Fetch job status from Redis. Returns None if not found."""
    raw = redis_connection.get(f"job:{file_id}")
    if not raw:
        return None
    return json.loads(raw)