# app/routers/folders.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.logger import logger
from app.core.security import get_current_active_user
from app.exceptions import ValidationException
from app.utils.constants import EMPTY_FOLDER_NAME
from app.services import create_folder, delete_folder, list_folders

router = APIRouter(tags=["folders"])

@router.post("/create_folder/")
async def create_folder_endpoint(name: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    """Create a new folder for the current user."""
    try:
        if not name:
            raise ValidationException(EMPTY_FOLDER_NAME)
            
        new_folder = await create_folder(db, name, current_user.id)
        
        logger.info(f"Folder '{name}' created successfully for user {current_user.username}")
        
        return {
            "message": f"Folder '{new_folder['name']}' created successfully",
            "folder": new_folder
        }
    except ValidationException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        raise

@router.delete("/folders/{folder_name}")
async def delete_folder_endpoint(folder_name: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    """Delete a folder and all its contents."""
    try:
        deleted_folder = await delete_folder(db, folder_name, current_user.id)
        
        logger.info(f"Folder '{folder_name}' and all its files deleted successfully by user {current_user.username}")
        return {"message": f"Folder '{deleted_folder}' and all its files deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting folder: {str(e)}")
        raise

@router.get("/folders/")
async def list_folders_endpoint(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    """List all folders belonging to the current user."""
    try:
        folders = await list_folders(db, current_user.id)
        logger.info(f"Folder list fetched successfully for user {current_user.username}")
        return folders
    except Exception as e:
        logger.error(f"Error fetching folder list: {e}")
        raise