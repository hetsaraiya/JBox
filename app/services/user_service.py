from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.security import get_password_hash, verify_password
from app.schemas import UserCreate

async def get_user_by_email(db: AsyncSession, email: str):
    """Get a user by email."""
    result = await db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
    user = result.fetchone()
    return user

async def get_user_by_username(db: AsyncSession, username: str):
    """Get a user by username."""
    result = await db.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username})
    user = result.fetchone()
    return user

async def create_user(db: AsyncSession, user_data: UserCreate):
    """Create a new user."""
    hashed_password = get_password_hash(user_data.password)
    
    query = text("""
        INSERT INTO users (email, username, hashed_password, is_active)
        VALUES (:email, :username, :hashed_password, :is_active)
        RETURNING id, email, username, is_active, created_at
    """)
    
    result = await db.execute(
        query, 
        {
            "email": user_data.email,
            "username": user_data.username,
            "hashed_password": hashed_password,
            "is_active": True
        }
    )
    
    new_user = result.fetchone()
    await db.commit()
    
    return new_user

async def authenticate_user(db: AsyncSession, username: str, password: str):
    """Authenticate a user by username and password."""
    user = await get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user