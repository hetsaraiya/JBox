from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.exceptions import NotFoundException, DatabaseException
from app.utils.constants import FOLDER_NOT_FOUND

async def create_folder(db: AsyncSession, name: str, user_id: int):
    """Create a new folder for a user."""
    try:
        # Check if folder name exists for this user
        result = await db.execute(
            text("SELECT name FROM folders WHERE name LIKE :name AND user_id = :user_id"), 
            {"name": f"{name}%", "user_id": user_id}
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
        
        result = await db.execute(query, {"name": name, "user_id": user_id})
        new_folder = result.fetchone()
        await db.commit()
        
        return {
            "id": new_folder.id, 
            "name": new_folder.name, 
            "user_id": new_folder.user_id
        }
    except Exception as e:
        await db.rollback()
        raise DatabaseException(f"Error creating folder: {str(e)}")

async def delete_folder(db: AsyncSession, folder_name: str, user_id: int):
    """Delete a folder and all its file chunks."""
    try:
        # Check if folder exists and belongs to the current user
        result = await db.execute(
            text("SELECT id FROM folders WHERE name = :name AND user_id = :user_id"),
            {"name": folder_name, "user_id": user_id}
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
        return folder_name
    except NotFoundException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise DatabaseException(f"Error deleting folder: {str(e)}")

async def list_folders(db: AsyncSession, user_id: int):
    """List all folders belonging to a user."""
    try:
        result = await db.execute(
            text("SELECT id, name FROM folders WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        folders = result.fetchall()
        return [{"id": folder.id, "name": folder.name} for folder in folders]
    except Exception as e:
        raise DatabaseException(f"Error listing folders: {str(e)}")

async def get_folder_by_id(db: AsyncSession, folder_id: int, user_id: int):
    """Get a folder by ID if it belongs to the user."""
    result = await db.execute(
        text("SELECT id, name, user_id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
        {"folder_id": folder_id, "user_id": user_id}
    )
    folder = result.fetchone()
    if not folder:
        raise NotFoundException(FOLDER_NOT_FOUND)
    return folder