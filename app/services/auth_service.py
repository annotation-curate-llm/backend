from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.core.exceptions import NotFoundError


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, user_data: UserCreate) -> User:
        user = (
            self.db.query(User)
            .filter(
                User.provider == user_data.provider,
                User.provider_id == user_data.provider_id,
            )
            .first()
        )

        if user:
            user.email = user_data.email
            user.name = user_data.name
            user.avatar_url = user_data.avatar_url
            user.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(user)
            return user

        new_user = User(**user_data.model_dump())
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user

    def get_user_by_id(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("User not found")
        return user

    def get_user_by_email(self, email: str) -> User:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise NotFoundError("User not found")
        return user

    def update_user_role(self, user_id: str, role: UserRole) -> User:
        user = self.get_user_by_id(user_id)
        user.role = role
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate_user(self, user_id: str) -> User:
        user = self.get_user_by_id(user_id)

        if not user.is_active:
            return user  # idempotent behavior 

        user.is_active = False
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)
        return user

    def activate_user(self, user_id: str) -> User:
        user = self.get_user_by_id(user_id)

        if user.is_active:
            return user

        user.is_active = True
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)
        return user
