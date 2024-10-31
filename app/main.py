# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .discord_bot import bot, DISCORD_TOKEN
from .routers import folders, files, status, root, test_db
import asyncio

CHUNK_SIZE = 24 * 1024 * 1024

app = FastAPI()

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

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    print("Bot started")

@app.on_event("shutdown")
async def shutdown_event():
    if bot.is_ready():
        await bot.close()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)