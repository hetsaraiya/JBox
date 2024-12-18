import fastapi
from fastapi import Request
from fastapi.templating import Jinja2Templates
from ..logger import logger

router = fastapi.APIRouter(tags=["root"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def root(request: Request):
    return {"message": "Hello World"}