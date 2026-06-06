from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.tenants import Tenant
from app.models.users import User, UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def _require_super_admin(current_user: User) -> None:
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can perform this action",
        )


def _require_admin_or_above(current_user: User) -> None:
    if current_user.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def _validate_tenant_for_role(db: Session, role: UserRole, tenant_id: int | None) -> None:
    if role == UserRole.super_admin:
        return
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required for tenant users",
        )
    tenant_exists = db.query(Tenant.id).filter(Tenant.id == tenant_id).first()
    if not tenant_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )


def _check_create_permissions(current_user: User, new_role: UserRole, new_tenant_id: int | None) -> None:
    if current_user.role == UserRole.super_admin:
        return
    if current_user.role == UserRole.tenant_admin:
        if new_role == UserRole.super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins cannot create super admin users",
            )
        if new_tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only create users within their own tenant",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to create users",
    )


def _check_update_permissions(current_user: User, target_user: User, update_data: dict) -> None:
    if current_user.role == UserRole.super_admin:
        return
    if current_user.id == target_user.id:
        forbidden_fields = {"role", "tenant_id", "is_active"}
        if forbidden_fields.intersection(update_data.keys()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot change your own role, tenant, or active status",
            )
        return
    if current_user.role == UserRole.tenant_admin:
        if target_user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only update users within their own tenant",
            )
        if target_user.role == UserRole.super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins cannot update super admin users",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to update other users",
    )


def _check_suspend_permissions(current_user: User, target_user: User) -> None:
    if current_user.role == UserRole.super_admin:
        return
    if current_user.role == UserRole.tenant_admin:
        if target_user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only suspend users within their own tenant",
            )
        if target_user.role in (UserRole.super_admin, UserRole.tenant_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only suspend tenant staff",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to suspend users",
    )


def _check_delete_permissions(current_user: User, target_user: User) -> None:
    if current_user.role == UserRole.super_admin:
        return
    if current_user.role == UserRole.tenant_admin:
        if target_user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only delete users within their own tenant",
            )
        if target_user.role in (UserRole.super_admin, UserRole.tenant_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only delete tenant staff",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to delete users",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_create_permissions(current_user, user.role, user.tenant_id)
    _validate_tenant_for_role(db, user.role, user.tenant_id)

    user_data = user.model_dump(exclude={"password"})
    if user.role == UserRole.super_admin:
        user_data["tenant_id"] = None

    db_user = User(**user_data, password_hash=get_password_hash(user.password))
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    db.refresh(db_user)
    return db_user


@router.get("/", response_model=list[UserOut])
def list_users(
    tenant_id: int | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    is_suspended: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin_or_above(current_user)

    query = db.query(User)

    if current_user.role == UserRole.tenant_admin:
        query = query.filter(User.tenant_id == current_user.tenant_id)
    elif tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)

    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_suspended is not None:
        query = query.filter(User.is_suspended == is_suspended)

    return query.order_by(User.created_at.desc()).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = _get_user_or_404(user_id, db)

    if current_user.role == UserRole.super_admin:
        return user
    if current_user.id == user_id:
        return user
    if current_user.role == UserRole.tenant_admin and user.tenant_id == current_user.tenant_id:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this user",
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = _get_user_or_404(user_id, db)
    update_data = user_update.model_dump(exclude_unset=True)
    _check_update_permissions(current_user, user, update_data)

    new_role = update_data.get("role", user.role)
    new_tenant_id = update_data.get("tenant_id", user.tenant_id)
    _validate_tenant_for_role(db, new_role, new_tenant_id)

    if new_role == UserRole.super_admin:
        update_data["tenant_id"] = None

    password = update_data.pop("password", None)
    if password is not None:
        user.password_hash = get_password_hash(password)

    for field, value in update_data.items():
        setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    db.refresh(user)
    return user


@router.post("/{user_id}/suspend", response_model=UserOut)
def suspend_user(
    user_id: int,
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = _get_user_or_404(user_id, db)
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot suspend yourself",
        )
    _check_suspend_permissions(current_user, user)
    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already suspended",
        )
    user.is_suspended = True
    user.suspension_reason = reason
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = _get_user_or_404(user_id, db)
    _check_suspend_permissions(current_user, user)
    if not user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not suspended",
        )
    user.is_suspended = False
    user.suspension_reason = None
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = _get_user_or_404(user_id, db)
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    _check_delete_permissions(current_user, user)
    db.delete(user)
    db.commit()