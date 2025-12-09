from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/oauth", response_model=UserResponse)
def oauth_signin(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Handle OAuth sign-in from frontend.
    Create user if doesn't exist, return user data.
    """
    # Check if user exists
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user:
        # Create new user
        user = User(
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar,
            provider=user_data.provider,
            provider_id=user_data.provider_id,
            role="annotator"  # Default role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user info
        user.name = user_data.name
        user.avatar_url = user_data.avatar
        db.commit()
        db.refresh(user)
    
    return user

@router.get("/me", response_model=UserResponse)
def get_current_user(user_id: str, db: Session = Depends(get_db)):
    """Get current user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user