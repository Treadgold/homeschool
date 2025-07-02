"""
Authentication utilities shared across the application
Extracted from main.py to avoid circular imports
"""

from fastapi import Depends, HTTPException, status, Cookie, Request
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
import os
from typing import Optional

from app.database import get_db
from app.models import User

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
SESSION_COOKIE = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
serializer = URLSafeTimedSerializer(SECRET_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """Hash a password for storing"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_session_cookie(user_id, max_age=SESSION_MAX_AGE):
    """Create a session cookie for a user"""
    return serializer.dumps({"user_id": user_id})

def get_current_user(request: Request, db: Session = Depends(get_db), session: str = Cookie(None)) -> Optional[User]:
    """Get the current user from session cookie"""
    if not session:
        return None
    try:
        data = serializer.loads(session, max_age=SESSION_MAX_AGE)
        user = db.query(User).filter(User.id == data["user_id"]).first()
        return user
    except (BadSignature, SignatureExpired):
        return None

def require_admin(user=Depends(get_current_user)) -> User:
    """Require an admin user"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

def create_email_token(email: str) -> str:
    """Create an email confirmation token"""
    return serializer.dumps({"email": email}, salt="email-confirm")

def verify_email_token(token: str) -> Optional[str]:
    """Verify an email confirmation token and return email"""
    try:
        data = serializer.loads(token, salt="email-confirm", max_age=86400)  # 24 hours
        return data["email"]
    except:
        return None

# CSRF token generation and validation
def generate_csrf_token() -> str:
    """Generate a CSRF token for forms"""
    return serializer.dumps({"csrf": "token"}, salt="csrf")

def verify_csrf_token(token: str) -> bool:
    """Verify a CSRF token"""
    try:
        serializer.loads(token, salt="csrf", max_age=3600)  # 1 hour expiry
        return True
    except:
        return False 