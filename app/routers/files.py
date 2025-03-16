from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db, AsyncSessionLocal
from app.logger import logger
from app.core.security import get_current_active_user
from app.core.config import settings
from app.exceptions import (
    NotFoundException, DatabaseException, FileOperationException, 
    DiscordBotException
)
from app.services import (
    get_folder_by_id, list_files, delete_file, get_file_chunks,
    create_file_download_stream, create_file_view_stream,
    ensure_bot_ready, upload_file_chunk
)
from app.models import FileChunk

router = APIRouter(tags=["files"])

@router.post("/upload/")
async def upload_file(file: UploadFile, folder_id: int, current_user = Depends(get_current_active_user)):
    """Upload a file to a specified folder."""
    uploaded_chunks = []
    try:
        channel = await ensure_bot_ready()
        if not channel:
            raise DiscordBotException("Discord channel not available")
        
        async with AsyncSessionLocal() as db:
            # Verify folder belongs to current user
            folder = await get_folder_by_id(db, folder_id, current_user.id)
            
            filename, extension = file.filename.rsplit('.', 1) if '.' in file.filename else (file.filename, '')
            result = await db.execute(
                text("SELECT file_name FROM file_chunks WHERE file_name LIKE :file_name AND folder_id = :folder_id"),
                {"file_name": f"{filename}%", "folder_id": folder_id}
            )
            existing_files = result.fetchall()
            if existing_files:
                count = len(existing_files)
                file.filename = f"{filename}_{count + 1}.{extension}" if extension else f"{filename}_{count + 1}"
            
            chunk_id = 0
            total_size = 0

            while True:
                chunk = await file.read(settings.CHUNK_SIZE)
                if not chunk:
                    break
                chunk_id += 1
                total_size += len(chunk)
                message_id = await upload_file_chunk(chunk, file.filename, chunk_id)

                chunk_entry = FileChunk(
                    file_name=file.filename,
                    chunk_id=chunk_id,
                    discord_message_id=message_id,
                    folder_id=folder_id
                )
                db.add(chunk_entry)
                uploaded_chunks.append(chunk_entry)

            await db.commit()
            
            logger.info(f"User {current_user.username} uploaded file {file.filename} to folder {folder_id}")
            
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "chunks": chunk_id
        }
    
    except Exception as e:
        logger.error(f"Error during file upload by user {current_user.username}: {str(e)}")
        # Handle cleanup of partially uploaded files
        from app.services import delete_message
        async with AsyncSessionLocal() as db:
            for chunk_entry in uploaded_chunks:
                try:
                    await db.execute(
                        "DELETE FROM file_chunks WHERE file_name = :file_name AND chunk_id = :chunk_id AND folder_id = :folder_id", 
                        {"file_name": chunk_entry.file_name, "chunk_id": chunk_entry.chunk_id, "folder_id": chunk_entry.folder_id}
                    )
                    await delete_message(chunk_entry.discord_message_id)
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
            await db.commit()
        
        raise FileOperationException(f"Error uploading file: {str(e)}")

@router.delete("/files/{file_name}")
async def delete_file_endpoint(file_name: str, folder_id: int, current_user = Depends(get_current_active_user)):
    """Delete a file from a folder."""
    try:
        async with AsyncSessionLocal() as db:
            await delete_file(db, file_name, folder_id, current_user.id)
            logger.info(f"User {current_user.username} deleted file {file_name} from folder {folder_id}")
            return {"message": f"File '{file_name}' deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise

@router.get("/files/{folder_id}")
async def list_files_endpoint(folder_id: int, current_user = Depends(get_current_active_user)):
    """List all files in a folder."""
    try:    
        async with AsyncSessionLocal() as db:
            files = await list_files(db, folder_id, current_user.id)
            logger.info(f"User {current_user.username} listed files in folder {folder_id}")
            return files
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise

@router.get("/download/{filename}")
async def download_file(filename: str, folder_id: int, current_user = Depends(get_current_active_user)):
    """Download a file from a folder."""
    try:
        async with AsyncSessionLocal() as db:
            chunks = await get_file_chunks(db, filename, folder_id, current_user.id)
            logger.info(f"User {current_user.username} downloaded file {filename} from folder {folder_id}")
            return await create_file_download_stream(filename, chunks)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise FileOperationException(f"Error downloading file: {str(e)}")  

@router.get("/open/{name}")
async def open_file(name: str, folder_id: int, current_user = Depends(get_current_active_user)):
    """Open a file for viewing in the browser."""
    try:
        async with AsyncSessionLocal() as db:
            chunks = await get_file_chunks(db, name, folder_id, current_user.id)
            logger.info(f"User {current_user.username} opened file {name} from folder {folder_id}")
            return await create_file_view_stream(name, chunks)
    except Exception as e:
        logger.error(f"Error opening file: {str(e)}")
        raise FileOperationException(f"Error opening file: {str(e)}")

@router.get("/view/{id}")
async def view_file_by_id(id: int, current_user = Depends(get_current_active_user)):
    """View a file by its ID."""
    try:
        async with AsyncSessionLocal() as db:
            # Get file info and verify ownership
            result = await db.execute(
                """
                SELECT fc.file_name, fc.folder_id, f.user_id 
                FROM file_chunks fc 
                JOIN folders f ON fc.folder_id = f.id 
                WHERE fc.id = :id
                """,
                {"id": id}
            )
            file_info = result.fetchone()
            
            if not file_info:
                raise NotFoundException(f"File with id {id} not found")
                
            # Check if file belongs to current user
            if file_info.user_id != current_user.id:
                raise FileOperationException("You don't have permission to access this file")
            
            # Now get the file chunks and return the streaming response
            chunks = await get_file_chunks(db, file_info.file_name, file_info.folder_id, current_user.id)
            logger.info(f"User {current_user.username} viewed file {file_info.file_name}")
            return await create_file_view_stream(file_info.file_name, chunks)
            
    except Exception as e:
        logger.error(f"Error viewing file: {str(e)}")
        raise FileOperationException(f"Error viewing file: {str(e)}")