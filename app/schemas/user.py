from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str]
    avatar: Optional[str]
    provider: str
    provider_id: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    role: str
    created_at: datetime

    class Config:
        from_attributes = True