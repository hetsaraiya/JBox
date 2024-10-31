# app/routers/test_db.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from sqlalchemy import text

router = APIRouter(tags=["test_db"])

@router.get("/test_db")
async def test_db_connection(db: AsyncSession = Depends(get_db)):
    try:
        async with db.begin():
            result = await db.execute(text("SELECT 1"))
            return {"status": "success", "result": result.scalar()}
    except Exception as e:
        return {"status": "error", "message": str(e)}