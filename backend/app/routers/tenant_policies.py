from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.tenant_policies import TenantPolicy
from app.models.users import User, UserRole
from app.schemas.tenant_policy import TenantPolicyCreate, TenantPolicyOut, TenantPolicyUpdate


router = APIRouter(prefix="/policies", tags=["policies"])


def _require_tenant_admin(current_user: User) -> None:
    if current_user.role not in (UserRole.tenant_admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can manage policies",
        )


def _get_policy_or_404(policy_id: int, tenant_id: int, db: Session) -> TenantPolicy:
    policy = db.query(TenantPolicy).filter(
        TenantPolicy.id == policy_id,
        TenantPolicy.tenant_id == tenant_id,
    ).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.get("/", response_model=list[TenantPolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(TenantPolicy).filter(
        TenantPolicy.tenant_id == current_user.tenant_id,
    ).order_by(TenantPolicy.display_order).all()


@router.post("/", response_model=TenantPolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: TenantPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_tenant_admin(current_user)
    policy = TenantPolicy(**payload.model_dump(), tenant_id=current_user.tenant_id)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.patch("/{policy_id}", response_model=TenantPolicyOut)
def update_policy(
    policy_id: int,
    payload: TenantPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_tenant_admin(current_user)
    policy = _get_policy_or_404(policy_id, current_user.tenant_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/{policy_id}/toggle", response_model=TenantPolicyOut)
def toggle_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_tenant_admin(current_user)
    policy = _get_policy_or_404(policy_id, current_user.tenant_id, db)
    policy.is_active = not policy.is_active
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_tenant_admin(current_user)
    policy = _get_policy_or_404(policy_id, current_user.tenant_id, db)
    db.delete(policy)
    db.commit()