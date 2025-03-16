from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.db.session import get_db
from app.schemas import UserCreate, UserResponse, Token, UserLogin
from app.core.security import (
    create_access_token, 
    get_current_active_user
)
from app.core.config import settings
from app.services import (
    create_user, 
    authenticate_user
)
from app.logger import logger
from app.exceptions import DatabaseException, ValidationException

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    try:
        # Check if email or username already exists
        result = await db.execute(
            "SELECT id FROM users WHERE email = :email OR username = :username", 
            {"email": user.email, "username": user.username}
        )
        existing_user = result.fetchone()
        
        if existing_user:
            # Check which field already exists
            if existing_user.email == user.email:
                raise ValidationException("Email already registered")
            else:
                raise ValidationException("Username already taken")
        
        new_user = await create_user(db, user)
        logger.info(f"User {user.username} registered successfully")
        
        return {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "is_active": new_user.is_active,
            "created_at": new_user.created_at
        }
    
    except ValidationException as e:
        raise e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise DatabaseException(f"Error creating user: {str(e)}")

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login and get an access token."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login_with_credentials(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with username and password and get an access token."""
    user = await authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """Get information about the currently authenticated user."""
    return current_user