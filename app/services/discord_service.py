import discord
import io
import asyncio
from fastapi import HTTPException
from discord.ext import commands

from app.core.config import settings
from app.logger import logger

class StorageBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)
        self.channel = None
        self.ready = asyncio.Event()
        
    async def setup_hook(self):
        logger.info(f"Bot is ready! Logged in as {self.user}")
        await self.ensure_channel()
        
    async def ensure_channel(self):
        try:
            self.channel = self.get_channel(settings.CHANNEL_ID)
            if not self.channel:
                for guild in self.guilds:
                    self.channel = guild.get_channel(settings.CHANNEL_ID)
                    if self.channel:
                        break
                if not self.channel:
                    self.channel = await self.fetch_channel(settings.CHANNEL_ID)
            if self.channel:
                logger.info(f"Successfully connected to channel: {self.channel.name}")
                self.ready.set()
            else:
                logger.error(f"Could not find channel with ID: {settings.CHANNEL_ID}")
        except Exception as e:
            logger.error(f"Error connecting to channel: {str(e)}")

    async def upload_chunk(self, chunk: bytes, filename: str, chunk_id: int) -> str:
        await self.ensure_channel()
        file = discord.File(fp=io.BytesIO(chunk), filename=f"{filename}.part{chunk_id}")
        message = await self.channel.send(content=f"Chunk {chunk_id} of {filename}", file=file)
        return str(message.id)

# Create a single instance of the bot
bot = StorageBot()

async def ensure_bot_ready():
    """Ensure the bot is ready and connected to the channel."""
    if not bot.is_ready():
        await bot.wait_until_ready()
    if not bot.channel:
        await bot.ensure_channel()
    if not bot.channel:
        raise HTTPException(
            status_code=500,
            detail=f"Could not connect to Discord channel {settings.CHANNEL_ID}."
        )
    return bot.channel

async def upload_file_chunk(chunk: bytes, filename: str, chunk_id: int):
    """Upload a file chunk to Discord."""
    return await bot.upload_chunk(chunk, filename, chunk_id)

async def get_bot_status():
    """Get the status of the Discord bot."""
    channel = await ensure_bot_ready()
    return {
        "bot_ready": bot.is_ready(),
        "channel_connected": bool(channel),
        "channel_id": channel.id if channel else None,
        "channel_name": channel.name if channel else None
    }

async def fetch_message(message_id: str):
    """Fetch a message from Discord by its ID."""
    await ensure_bot_ready()
    return await bot.channel.fetch_message(message_id)

async def delete_message(message_id: str):
    """Delete a message from Discord."""
    await ensure_bot_ready()
    try:
        message = await bot.channel.fetch_message(message_id)
        await message.delete()
        return True
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {e}")
        return False

async def start_bot(token: str):
    """Start the Discord bot."""
    asyncio.create_task(bot.start(token))
    
async def close_bot():
    """Close the Discord bot connection."""
    if bot.is_ready():
        await bot.close()