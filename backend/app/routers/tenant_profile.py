from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.tenant_profile import TenantProfile
from app.models.users import User, UserRole
from app.schemas.tenant_profile import TenantProfileCreate, TenantProfileOut, TenantProfileUpdate


router = APIRouter(prefix="/tenant-profile", tags=["tenant-profile"])


def _require_tenant_admin(current_user: User) -> None:
    if current_user.role not in (UserRole.tenant_admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can manage the tenant profile",
        )


@router.get("/", response_model=TenantProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(TenantProfile).filter(
        TenantProfile.tenant_id == current_user.tenant_id,
    ).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not set up yet")
    return profile


@router.post("/", response_model=TenantProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: TenantProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_tenant_admin(current_user)
    existing = db.query(TenantProfile).filter(
        TenantProfile.tenant_id == current_user.tenant_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PATCH to update.",
        )
    contract_prefix = f"T{current_user.tenant_id}"
    profile = TenantProfile(
        **payload.model_dump(),
        tenant_id=current_user.tenant_id,
        contract_prefix=contract_prefix,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/", response_model=TenantProfileOut)
def update_profile(
    payload: TenantProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_tenant_admin(current_user)
    profile = db.query(TenantProfile).filter(
        TenantProfile.tenant_id == current_user.tenant_id,
    ).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not set up yet")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile