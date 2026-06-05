from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class TenantBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone_number: Optional[str] = Field(default=None, max_length=50)
    plan: Literal["starter", "pro", "enterprise"] = "starter"
    is_active: bool = True


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(default=None, max_length=50)
    plan: Optional[Literal["starter", "pro", "enterprise"]] = None
    is_active: Optional[bool] = None


class TenantOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    plan: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}