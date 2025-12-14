from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user_id
from app.models.user import User
from typing import Optional

def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from database"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user