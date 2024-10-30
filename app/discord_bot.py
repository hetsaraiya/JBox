# app/discord_bot.py
import discord
import io
import asyncio
from fastapi import HTTPException
from discord.ext import commands
from .config import DISCORD_TOKEN, CHANNEL_ID

CHUNK_SIZE = 24 * 1024 * 1024

class StorageBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)
        self.channel = None
        self.ready = asyncio.Event()
        
    async def setup_hook(self):
        print(f"Bot is ready! Logged in as {self.user}")
        await self.ensure_channel()
        
    async def ensure_channel(self):
        try:
            self.channel = self.get_channel(CHANNEL_ID)
            if not self.channel:
                for guild in self.guilds:
                    self.channel = guild.get_channel(CHANNEL_ID)
                    if self.channel:
                        break
                if not self.channel:
                    self.channel = await self.fetch_channel(CHANNEL_ID)
            if self.channel:
                print(f"Successfully connected to channel: {self.channel.name}")
                self.ready.set()
            else:
                print(f"Could not find channel with ID: {CHANNEL_ID}")
        except Exception as e:
            print(f"Error connecting to channel: {str(e)}")

    async def upload_chunk(self, chunk: bytes, filename: str, chunk_id: int) -> str:
        await self.ensure_channel()
        file = discord.File(fp=io.BytesIO(chunk), filename=f"{filename}.part{chunk_id}")
        message = await self.channel.send(content=f"Chunk {chunk_id} of {filename}", file=file)
        return str(message.id)

bot = StorageBot()

async def ensure_bot_ready():
    if not bot.is_ready():
        await bot.wait_until_ready()
    if not bot.channel:
        await bot.ensure_channel()
    if not bot.channel:
        raise HTTPException(
            status_code=500,
            detail=f"Could not connect to Discord channel {CHANNEL_ID}."
        )
    return bot.channel
