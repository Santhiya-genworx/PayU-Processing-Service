import json
from datetime import date, datetime
from src.data.clients.redis import redis_connection

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat() 
        return super().default(obj)

def set_job_status(file_id: str, status: str, result=None, error=None):
    payload = {
        "status": status,
        "result": result,
        "error": error,
    }
    redis_connection.setex(
        f"job:{file_id}",
        3600,
        json.dumps(payload, cls=SafeEncoder)  
    )

def get_job_status(file_id: str) -> dict | None:
    raw = redis_connection.get(f"job:{file_id}")
    if not raw:
        return None
    return json.loads(raw)