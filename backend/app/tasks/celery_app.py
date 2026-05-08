from celery import Celery
from celery.schedules import schedule

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "suit_api",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.monitor_tasks",
        "app.tasks.billing_tasks",
    ],
)

celery_app.conf.timezone = settings.timezone
celery_app.conf.task_default_queue = "default"
celery_app.conf.beat_schedule = {
    "collect-gpu-metrics-every-30-seconds": {
        "task": "app.tasks.monitor_tasks.collect_gpu_metrics",
        "schedule": schedule(settings.gpu_metrics_interval_seconds),
    },
    "check-node-heartbeat-every-30-seconds": {
        "task": "app.tasks.monitor_tasks.check_node_heartbeat",
        "schedule": schedule(settings.gpu_metrics_interval_seconds),
    },
    "calculate-billing-every-5-minutes": {
        "task": "app.tasks.billing_tasks.calculate_billing",
        "schedule": schedule(300),
    },
}
