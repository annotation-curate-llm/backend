from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from datetime import datetime
from typing import Optional

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_user(self, user_data: UserCreate) -> User:
        """Get existing user or create new one from OAuth data"""
        # Check if user exists by provider and provider_id
        existing_user = self.db.query(User).filter(
            User.provider == user_data.provider,
            User.provider_id == user_data.provider_id
        ).first()
        
        if existing_user:
            # Update existing user info
            existing_user.email = user_data.email
            existing_user.name = user_data.name
            existing_user.avatar_url = user_data.avatar_url
            existing_user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_user)
            return existing_user
        
        # Create new user
        new_user = User(**user_data.model_dump())
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def update_user_role(self, user_id: str, role: UserRole) -> Optional[User]:
        """Update user role (admin only)"""
        user = self.get_user_by_id(user_id)
        if user:
            user.role = role
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def deactivate_user(self, user_id: str) -> Optional[User]:
        """Deactivate user account"""
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def activate_user(self, user_id: str) -> Optional[User]:
        """Activate user account"""
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = True
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
        return user