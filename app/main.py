# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .discord_bot import bot, DISCORD_TOKEN
from .routers import folders, files, status, root, test_db
from .websocket_manager import manager
import asyncio
from fastapi.responses import FileResponse

app = FastAPI()

favicon_path = 'favicon.ico'

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_db.router)
app.include_router(root.router)
app.include_router(folders.router)
app.include_router(files.router)
app.include_router(status.router)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.state").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.info("Discord bot has been started.")

@app.on_event("shutdown")
async def shutdown_event():
    if bot.is_ready():
        await bot.close()

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(5)
            await manager.send_message("Test message")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)