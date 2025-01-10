from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.constants import *

class BaseAPIException(Exception):
    def __init__(self, detail: str, status_code: int):
        self.detail = detail
        self.status_code = status_code

class NotFoundException(BaseAPIException):
    def __init__(self, detail: str = NOT_FOUND):
        super().__init__(detail=detail, status_code=404)

class DatabaseException(BaseAPIException):
    def __init__(self, detail: str = DATABASE_ERROR):
        super().__init__(detail=detail, status_code=500)

class FileOperationException(BaseAPIException):
    def __init__(self, detail: str = FILE_OPERATION_ERROR):
        super().__init__(detail=detail, status_code=500)

class DiscordBotException(BaseAPIException):
    def __init__(self, detail: str = DISCORD_BOT_ERROR):
        super().__init__(detail=detail, status_code=503)

class ValidationException(BaseAPIException):
    def __init__(self, detail: str = INVALID_REQUEST):
        super().__init__(detail=detail, status_code=400)

async def base_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": [],
            "message": exc.detail,
            "error": str(exc.detail),
            "status": False
        }
    )

async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content={
            "data": [],
            "message": NOT_FOUND,
            "error": str(exc.detail),
            "status": False
        }
    )

async def database_exception_handler(request: Request, exc: DatabaseException):
    return JSONResponse(
        status_code=500,
        content={
            "data": [],
            "message": DATABASE_ERROR,
            "error": str(exc.detail),
            "status": False
        }
    )

async def file_operation_exception_handler(request: Request, exc: FileOperationException):
    return JSONResponse(
        status_code=500,
        content={**ERROR_RESPONSE, "error": str(exc.detail)}
    )

async def discord_bot_exception_handler(request: Request, exc: DiscordBotException):
    return JSONResponse(
        status_code=503,
        content={
            "data": [],
            "message": DISCORD_BOT_ERROR,
            "error": str(exc.detail),
            "status": False
        }
    )

async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=400,
        content={
            "data": [],
            "message": VALIDATION_ERROR,
            "error": str(exc.detail),
            "status": False
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "data": [],
            "message": INTERNAL_SERVER_ERROR,
            "error": str(exc),
            "status": False
        }
    )