from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from services.db import get_db, User
from models import UserCreate, UserResponse, Token
from middleware.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user into the SaaS platform."""
    # Check if user already exists
    db_user = db.query(User).filter((User.email == user.email) | (User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    hashed_pw = get_password_hash(user.password)
    new_user = User(
        email=user.email, 
        username=user.username, 
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticates a user and returns a JWT token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Returns the profile data of the currently authenticated user."""
    return current_user