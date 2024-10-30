# app/config.py
import os
from dotenv import load_dotenv


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env file")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID not found in .env file")

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    raise ValueError("CHANNEL_ID must be a number")
