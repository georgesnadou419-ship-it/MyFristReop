import json
from datetime import datetime, timezone

import redis

from app.config import settings
from app.utils.exceptions import AppException


class QueueService:
    QUEUES = {
        "high": "suit:queue:high",
        "normal": "suit:queue:normal",
        "low": "suit:queue:low",
    }
    FINISHED_CHANNEL = "suit:task:finished"
    NEW_TASK_CHANNEL = "suit:queue:new"

    def __init__(self):
        self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    @classmethod
    def get_queue_level(cls, priority: int) -> str:
        if priority >= 10:
            return "high"
        if priority < 0:
            return "low"
        return "normal"

    def enqueue_task(self, task_id: str, priority: int) -> None:
        payload = json.dumps(
            {
                "task_id": task_id,
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        queue_level = self.get_queue_level(priority)
        queue_name = self.QUEUES[queue_level]
        try:
            self.redis.lpush(queue_name, payload)
            self.redis.publish(self.NEW_TASK_CHANNEL, json.dumps({"task_id": task_id}))
        except redis.RedisError as exc:
            raise AppException(status_code=503, message="redis queue unavailable") from exc

    def publish_task_finished(self, task_id: str) -> None:
        try:
            self.redis.publish(self.FINISHED_CHANNEL, json.dumps({"task_id": task_id}))
        except redis.RedisError as exc:
            raise AppException(status_code=503, message="redis publish unavailable") from exc
