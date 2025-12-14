from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/sync-user", response_model=UserResponse)
def sync_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Sync user from OAuth provider (called by NextAuth)
    Creates user if doesn't exist, updates if exists
    """
    # Check if user exists
    existing_user = db.query(User).filter(
        User.provider == user_data.provider,
        User.provider_id == user_data.provider_id
    ).first()

    if existing_user:
        # Update existing user
        existing_user.email = user_data.email
        existing_user.name = user_data.name
        existing_user.avatar_url = user_data.avatar_url
        existing_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_user)
        return existing_user
    
    # Create new user
    new_user = User(**user_data.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user