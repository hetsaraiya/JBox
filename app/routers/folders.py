# app/routers/folders.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi.templating import Jinja2Templates
from ..database import get_db
from ..models import Folder
from ..logger import logger
from ..utils.auth import get_current_active_user
from app.exceptions import (
    NotFoundException, DatabaseException, ValidationException
)
from app.utils.constants import (
    EMPTY_FOLDER_NAME,
    FOLDER_NOT_FOUND,
    FOLDER_CREATE_ERROR,
    FOLDER_DELETE_ERROR
)

router = APIRouter(tags=["folders"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/create_folder/")
async def create_folder(name: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    try:
        if not name:
            raise ValidationException(EMPTY_FOLDER_NAME)
            
        # Check if folder name exists for this user
        result = await db.execute(
            text("SELECT name FROM folders WHERE name LIKE :name AND user_id = :user_id"), 
            {"name": f"{name}%", "user_id": current_user.id}
        )
        existing_folders = result.fetchall()
        
        if existing_folders:
            name = f"{name}_{len(existing_folders) + 1}"
        
        # Insert new folder with user_id
        query = text("""
            INSERT INTO folders (name, user_id)
            VALUES (:name, :user_id)
            RETURNING id, name, user_id
        """)
        
        result = await db.execute(query, {"name": name, "user_id": current_user.id})
        new_folder = result.fetchone()
        await db.commit()
        
        logger.info(f"Folder '{name}' created successfully for user {current_user.username}")
        
        return {
            "message": f"Folder '{name}' created successfully",
            "folder": {"id": new_folder.id, "name": new_folder.name, "user_id": new_folder.user_id}
        }
    except ValidationException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        raise DatabaseException(f"{FOLDER_CREATE_ERROR}: {str(e)}")

@router.delete("/folders/{folder_name}")
async def delete_folder(folder_name: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    try:
        # Check if folder exists and belongs to the current user
        result = await db.execute(
            text("SELECT id FROM folders WHERE name = :name AND user_id = :user_id"),
            {"name": folder_name, "user_id": current_user.id}
        )
        folder = result.fetchone()
        
        if not folder:
            raise NotFoundException(FOLDER_NOT_FOUND)
        
        folder_id = folder.id
        
        # Delete all file chunks in the folder
        await db.execute(
            text("DELETE FROM file_chunks WHERE folder_id = :folder_id"), 
            {"folder_id": folder_id}
        )
        
        # Delete the folder
        await db.execute(
            text("DELETE FROM folders WHERE id = :id"), 
            {"id": folder_id}
        )
        
        await db.commit()
        logger.info(f"Folder '{folder_name}' and all its files deleted successfully by user {current_user.username}")
        return {"message": f"Folder '{folder_name}' and all its files deleted successfully"}
    except NotFoundException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting folder: {str(e)}")
        raise DatabaseException(f"{FOLDER_DELETE_ERROR}: {str(e)}")

@router.get("/folders/")
async def list_folders(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    try:
        # Get only folders belonging to the current user
        result = await db.execute(
            text("SELECT id, name FROM folders WHERE user_id = :user_id"),
            {"user_id": current_user.id}
        )
        folders = result.fetchall()
        logger.info(f"Folder list fetched successfully for user {current_user.username}")
        return [{"id": folder.id, "name": folder.name} for folder in folders]
    except Exception as e:
        logger.error(f"Error fetching folder list: {e}")
        raise HTTPException(status_code=500, detail="Error fetching folder list.")