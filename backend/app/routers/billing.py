from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.billing import BillingRecordsPage, BillingSummary
from app.services.billing_service import get_billing_summary, list_billing_records
from app.utils.responses import success_response


router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.get("/summary")
def billing_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = BillingSummary.model_validate(get_billing_summary(db, current_user)).model_dump(mode="json")
    return success_response(data)


@router.get("/records")
def billing_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = BillingRecordsPage.model_validate(
        list_billing_records(db, current_user, page=page, page_size=page_size)
    ).model_dump(mode="json")
    return success_response(data)
