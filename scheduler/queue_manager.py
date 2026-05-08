import json
import logging
import time
from collections.abc import Iterable

import redis

logger = logging.getLogger(__name__)


class QueueManager:
    QUEUES = {
        "high": "suit:queue:high",
        "normal": "suit:queue:normal",
        "low": "suit:queue:low",
    }
    CHANNEL_NEW_TASK = "suit:queue:new"
    CHANNEL_TASK_FINISHED = "suit:task:finished"

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def enqueue(self, task_id: str, priority: int = 0) -> None:
        queue_name = self._get_queue_name(priority)
        payload = json.dumps({"task_id": task_id, "priority": priority, "enqueued_at": time.time()})
        try:
            self.redis.lpush(queue_name, payload)
            self.redis.publish(self.CHANNEL_NEW_TASK, json.dumps({"task_id": task_id}))
        except redis.RedisError:
            logger.exception("failed to enqueue task %s into redis", task_id)

    def dequeue(self) -> dict | None:
        try:
            for queue_name in self.QUEUES.values():
                raw = self.redis.rpop(queue_name)
                if raw:
                    return json.loads(raw)
        except redis.RedisError:
            logger.exception("failed to dequeue task from redis")
        return None

    def requeue(self, task_data: dict) -> None:
        priority = int(task_data.get("priority", 0) or 0)
        queue_name = self._get_queue_name(priority)
        try:
            self.redis.rpush(queue_name, json.dumps(task_data))
        except redis.RedisError:
            logger.exception("failed to requeue task payload: %s", task_data)

    def queue_length(self) -> dict[str, int]:
        try:
            return {
                name: self.redis.llen(queue_name)
                for name, queue_name in self.QUEUES.items()
            }
        except redis.RedisError:
            logger.exception("failed to fetch queue length from redis")
            return {name: 0 for name in self.QUEUES}

    def total_pending(self) -> int:
        return sum(self.queue_length().values())

    def create_pubsub(self):
        try:
            return self.redis.pubsub(ignore_subscribe_messages=True)
        except redis.RedisError:
            logger.exception("failed to create redis pubsub")
            raise

    def subscribe(self, pubsub, channels: Iterable[str]) -> None:
        try:
            pubsub.subscribe(*channels)
        except redis.RedisError:
            logger.exception("failed to subscribe redis pubsub channels: %s", list(channels))
            raise

    def _get_queue_name(self, priority: int) -> str:
        if priority >= 10:
            return self.QUEUES["high"]
        if priority >= 0:
            return self.QUEUES["normal"]
        return self.QUEUES["low"]
