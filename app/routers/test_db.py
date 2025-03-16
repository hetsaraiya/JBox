# app/routers/test_db.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.logger import logger

router = APIRouter(tags=["test_db"])

@router.get("/test_db")
async def test_db_connection(db: AsyncSession = Depends(get_db)):
    """Test database connection."""
    try:
        async with db.begin():
            result = await db.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return {"status": "success", "result": result.scalar()}
    except Exception as e:
        logger.error("Error testing database connection: %s", e)
        raise HTTPException(status_code=500, detail=f"Error testing database connection: {str(e)}")