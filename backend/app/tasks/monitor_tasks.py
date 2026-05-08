from app.database import SessionLocal
from app.services.monitor_service import collect_gpu_metrics as collect_metrics_service
from app.services.monitor_service import mark_offline_nodes
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.monitor_tasks.collect_gpu_metrics")
def collect_gpu_metrics() -> dict:
    db = SessionLocal()
    try:
        collected = collect_metrics_service(db)
        return {"collected": collected}
    finally:
        db.close()


@celery_app.task(name="app.tasks.monitor_tasks.check_node_heartbeat")
def check_node_heartbeat() -> dict:
    db = SessionLocal()
    try:
        offline_nodes = mark_offline_nodes(db)
        return {"offline_nodes": offline_nodes}
    finally:
        db.close()
