from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime
from typing import Optional
from app.config import settings
from app.models.user import UserRole

security = HTTPBearer()

def verify_token(token: str) -> dict:
    """Verify JWT token from NextAuth"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Extract user ID from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    return user_id

def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Extract user role from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    role: str = payload.get("role")
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Role not found in token"
        )
    return role

def require_role(allowed_roles: list[UserRole]):
    """Dependency to check if user has required role"""
    def role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        token = credentials.credentials
        payload = verify_token(token)
        user_role = payload.get("role")
        
        if user_role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return payload
    return role_checker