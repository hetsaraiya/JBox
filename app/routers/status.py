# app/routers/status.py
from fastapi import APIRouter
from ..discord_bot import bot, ensure_bot_ready

router = APIRouter(tags=["status"])

@router.get("/status/")
async def get_status():
    channel = await ensure_bot_ready()
    return {
        "bot_ready": bot.is_ready(),
        "channel_connected": bool(channel),
        "channel_id": channel.id if channel else None,
        "channel_name": channel.name if channel else None
    }
