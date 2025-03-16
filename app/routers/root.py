import fastapi
from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.logger import logger
from app.core.config import settings

router = fastapi.APIRouter(tags=["root"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def root(request: Request):
    """Root endpoint that returns a welcome message."""
    logger.info("Root endpoint accessed")
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "status": "active"
    }