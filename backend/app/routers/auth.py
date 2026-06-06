from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.subscription import get_subscription_warning
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenOut
from app.schemas.user import UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash if user else ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact your administrator.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "tenant_id": user.tenant_id,
            "role": user.role,
        },
    )

    return TokenOut(access_token=access_token, token_type="bearer", user=user)


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/subscription-status")
def get_my_subscription_status(
    current_user: User = Depends(get_current_user),
    warning: dict | None = Depends(get_subscription_warning),
):
    tenant = current_user.tenant
    if tenant is None:
        return {"subscription_status": None, "warning": None}

    return {
        "subscription_status": tenant.subscription_status,
        "trial_ends_at": tenant.trial_ends_at,
        "subscription_ends_at": tenant.subscription_ends_at,
        "grace_period_ends_at": tenant.grace_period_ends_at,
        "plan": tenant.plan,
        "warning": warning,
    }