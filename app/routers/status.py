# app/routers/status.py
from fastapi import APIRouter
from ..discord_bot import bot, ensure_bot_ready

router = APIRouter(tags=["status"])

@router.get("/status/")
async def get_status():
    try:
        channel = await ensure_bot_ready()
        return {
            "bot_ready": bot.is_ready(),
            "channel_connected": bool(channel),
            "channel_id": channel.id if channel else None,
            "channel_name": channel.name if channel else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@router.get("/status/bot")
async def get_bot_status():
    return {
        "bot_ready": bot.is_ready()
    }

@router.get("/status/guilds")
async def get_guilds():
    try:
        new= await ensure_bot_ready()
        return {
            "channel" : bool(new)
        }
    except Exception as e:
        return{"status": "error", "message": str(e)}


@router.get("/status/channel")
async def get_channel_status():
    try:
        channel = await ensure_bot_ready()
        return {
            "channel_connected": bool(channel),
            "channel_id": channel.id if channel else None,
            "channel_name": channel.name if channel else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}