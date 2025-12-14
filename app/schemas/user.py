from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from typing import Optional
from app.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    provider: str
    provider_id: str
    role: UserRole = UserRole.ANNOTATOR

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    id: UUID4
    provider: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserInDB(UserResponse):
    provider_id: str