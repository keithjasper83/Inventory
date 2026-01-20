from typing import Annotated
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth import auth_service
from src.models import User
from src.config import settings

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user

def require_user(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}, # Or Redirect
        )
    return user

def require_role(role: str):
    """
    Decorator to require a specific role for an endpoint.
    Usage: user = Depends(require_role("admin"))
    """
    def role_checker(user: User = Depends(require_user)):
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required role: {role}"
            )
        return user
    return role_checker

# Common role requirements
require_admin = require_role("admin")
require_reviewer = require_role("reviewer")

# Template config
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="src/templates")
