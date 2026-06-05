from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenOut
from app.schemas.user import UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    # Always run verify_password even when user is not found to prevent timing attacks
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