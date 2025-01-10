# app/routers/status.py
from fastapi import APIRouter, HTTPException
from ..discord_bot import bot, ensure_bot_ready
from ..logger import logger
from app.exceptions import DiscordBotException

router = APIRouter(tags=["status"])

@router.get("/status/")
async def get_status():
    try:
        channel = await ensure_bot_ready()
        logger.info("Getting bot status")
        return {
            "bot_ready": bot.is_ready(),
            "channel_connected": bool(channel),
            "channel_id": channel.id if channel else None,
            "channel_name": channel.name if channel else None
        }
    except Exception as e:
        logger.error("Error getting bot status: %s", e)
        raise DiscordBotException(f"Error getting bot status: {str(e)}")