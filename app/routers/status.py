# app/routers/status.py
from fastapi import APIRouter
from app.logger import logger
from app.exceptions import DiscordBotException
from app.services import get_bot_status

router = APIRouter(tags=["status"])

@router.get("/status/")
async def get_status_endpoint():
    """Get the status of the Discord bot."""
    try:
        logger.info("Getting bot status")
        return await get_bot_status()
    except Exception as e:
        logger.error("Error getting bot status: %s", e)
        raise DiscordBotException(f"Error getting bot status: {str(e)}")