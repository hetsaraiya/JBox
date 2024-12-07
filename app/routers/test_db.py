# app/routers/test_db.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from sqlalchemy import text
from ..logger import logger

router = APIRouter(tags=["test_db"])

@router.get("/test_db")
async def test_db_connection(db: AsyncSession = Depends(get_db)):
    try:
        async with db.begin():
            result = await db.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return {"status": "success", "result": result.scalar()}
    except Exception as e:
        logger.error("Error testing database connection: %s", e)
        raise HTTPException(status_code=500, detail="Error testing database connection")