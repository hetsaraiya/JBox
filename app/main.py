# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from fastapi.responses import FileResponse

from app.db.base import Base
from app.db.session import engine
from app.services import start_bot, close_bot 
from app.core.config import settings
from app.routers import folders, files, status, root, test_db, auth
from app.exceptions import (
    BaseAPIException,
    NotFoundException,
    DatabaseException,
    FileOperationException,
    DiscordBotException,
    ValidationException,
    base_exception_handler,
    general_exception_handler,
    not_found_exception_handler,
    database_exception_handler,
    file_operation_exception_handler,
    discord_bot_exception_handler,
    validation_exception_handler
)

app = FastAPI(
    title=settings.APP_NAME,
    description="JBox - A file storage system using Discord as a backend",
    version="1.0.0",
)

favicon_path = 'favicon.ico'

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(test_db.router)
app.include_router(root.router)
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(files.router)
app.include_router(status.router)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)

# Configure exception handlers
app.add_exception_handler(NotFoundException, not_found_exception_handler)
app.add_exception_handler(DatabaseException, database_exception_handler)
app.add_exception_handler(FileOperationException, file_operation_exception_handler)
app.add_exception_handler(DiscordBotException, discord_bot_exception_handler)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    # Create database tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start Discord bot
    await start_bot(settings.DISCORD_TOKEN)
    
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.state").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.info("Discord bot has been started.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    await close_bot()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)