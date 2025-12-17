from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

def create_access_token(user: User) -> str:
    """
    Create JWT token with user info INCLUDING ROLE
    This is critical for role-based access control
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,  # ← CRITICAL: Include role in token
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


@router.post("/sync-user", response_model=UserResponse)
def sync_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Sync user from OAuth provider (called by NextAuth)
    Creates user if doesn't exist, updates if exists
    """
    existing_user = db.query(User).filter(
        User.provider == user_data.provider,
        User.provider_id == user_data.provider_id
    ).first()

    if existing_user:
        existing_user.email = user_data.email
        existing_user.name = user_data.name
        existing_user.avatar_url = user_data.avatar_url
        existing_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_user)
        return existing_user
    
    new_user = User(**user_data.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/token")
def generate_token(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Generate JWT token after OAuth authentication
    Returns token WITH role included for RBAC
    
    Frontend flow:
    1. User authenticates with OAuth (Google, GitHub, etc.)
    2. Frontend calls this endpoint with user data
    3. Backend creates/updates user and returns JWT token
    4. Frontend stores token and uses it for all API requests
    """
    # Sync or get user
    user = db.query(User).filter(
        User.provider == user_data.provider,
        User.provider_id == user_data.provider_id
    ).first()
    
    if not user:
        user = User(**user_data.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Generate token with role
    access_token = create_access_token(user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.get("/verify")
def verify_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Verify if token is valid and return user info
    Useful for frontend to check authentication status
    """
    from app.core.dependencies import get_current_user
    
    user = get_current_user(credentials, db)
    
    return {
        "valid": True,
        "user": UserResponse.model_validate(user)
    }