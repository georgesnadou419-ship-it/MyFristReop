from app.database import SessionLocal
from app.services.billing_service import calculate_task_billing
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.billing_tasks.calculate_billing")
def calculate_billing() -> dict:
    db = SessionLocal()
    try:
        billed = calculate_task_billing(db)
        return {"billed_tasks": billed}
    finally:
        db.close()
