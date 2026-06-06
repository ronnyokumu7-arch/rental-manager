from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.jobs.booking_jobs import run_booking_auto_archive
from app.jobs.subscription_jobs import run_subscription_lifecycle
from app.models.users import User, UserRole
from fastapi import HTTPException, status


router = APIRouter(prefix="/admin", tags=["admin"])


def _require_super_admin(current_user: User) -> None:
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can perform this action",
        )


@router.post("/jobs/run-subscription-lifecycle")
def trigger_subscription_lifecycle(
    current_user: User = Depends(get_current_user),
):
    _require_super_admin(current_user)
    run_subscription_lifecycle()
    return {"message": "Subscription lifecycle job completed"}


@router.post("/jobs/run-booking-archive")
def trigger_booking_archive(
    current_user: User = Depends(get_current_user),
):
    _require_super_admin(current_user)
    run_booking_auto_archive()
    return {"message": "Booking auto-archive job completed"}