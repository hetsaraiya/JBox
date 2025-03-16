from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi.responses import StreamingResponse
from typing import List

from app.exceptions import NotFoundException, DatabaseException, FileOperationException
from app.utils.constants import FILE_NOT_FOUND
from app.models import FileChunk
import mimetypes

# This will be replaced with the modularized Discord bot in discord_service.py
from app.services.discord_service import bot, ensure_bot_ready

async def list_files(db: AsyncSession, folder_id: int, user_id: int):
    """List all files in a folder belonging to a user."""
    try:
        # Verify folder belongs to current user
        result = await db.execute(
            text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
            {"folder_id": folder_id, "user_id": user_id}
        )
        folder = result.fetchone()
        if not folder:
            raise NotFoundException(f"Folder with id {folder_id} not found or does not belong to you")
            
        result = await db.execute(
            text("SELECT DISTINCT file_name FROM file_chunks WHERE folder_id = :folder_id"),
            {"folder_id": folder_id}
        )
        files = result.fetchall()
        return [{"name": f[0]} for f in files]
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise DatabaseException(f"Error listing files: {str(e)}")

async def delete_file(db: AsyncSession, file_name: str, folder_id: int, user_id: int):
    """Delete a file and all its chunks from Discord."""
    try:
        # Verify folder belongs to current user
        result = await db.execute(
            text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
            {"folder_id": folder_id, "user_id": user_id}
        )
        folder = result.fetchone()
        if not folder:
            raise NotFoundException(f"Folder with id {folder_id} not found or does not belong to you")
            
        result = await db.execute(
            text("SELECT discord_message_id FROM file_chunks WHERE file_name = :file_name AND folder_id = :folder_id"),
            {"file_name": file_name, "folder_id": folder_id}
        )
        file_chunks = result.fetchall()
        
        if not file_chunks:
            raise NotFoundException(f"File {file_name} not found in folder {folder_id}")
            
        await db.execute(
            text("DELETE FROM file_chunks WHERE file_name = :file_name AND folder_id = :folder_id"),
            {"file_name": file_name, "folder_id": folder_id}
        )
        await db.commit()
        
        channel = await ensure_bot_ready()
        if channel:
            for chunk in file_chunks:
                try:
                    message = await channel.fetch_message(chunk.discord_message_id)
                    await message.delete()
                except Exception:
                    # Log error but continue with deletion
                    pass
        
        return file_name
    except NotFoundException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise FileOperationException(f"Error deleting file: {str(e)}")

async def get_file_chunks(db: AsyncSession, filename: str, folder_id: int, user_id: int):
    """Get all chunks for a file."""
    # Verify folder belongs to current user
    result = await db.execute(
        text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
        {"folder_id": folder_id, "user_id": user_id}
    )
    folder = result.fetchone()
    if not folder:
        raise NotFoundException(f"Folder with id {folder_id} not found or does not belong to you")
    
    result = await db.execute(
        text("SELECT chunk_id, discord_message_id FROM file_chunks WHERE file_name = :filename AND folder_id = :folder_id ORDER BY chunk_id"),
        {"filename": filename, "folder_id": folder_id}
    )
    chunks = result.fetchall()
    
    if not chunks:
        raise NotFoundException(f"File {filename} not found in folder {folder_id}")
    
    return chunks

async def create_file_download_stream(filename: str, chunks):
    """Create a streaming response for file download."""
    async def file_generator():
        for chunk_id, discord_message_id in chunks:
            try:
                message = await bot.channel.fetch_message(discord_message_id)
                attachment = message.attachments[0]
                chunk = await attachment.read()
                yield chunk
            except Exception as e:
                raise FileOperationException(f"Failed to fetch chunk {chunk_id} from Discord: {str(e)}")
                
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    return StreamingResponse(
        file_generator(), 
        media_type="application/octet-stream", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

async def create_file_view_stream(filename: str, chunks):
    """Create a streaming response for viewing a file."""
    async def file_generator():
        for chunk_id, discord_message_id in chunks:
            try:
                message = await bot.channel.fetch_message(discord_message_id)
                attachment = message.attachments[0]
                chunk = await attachment.read()
                yield chunk
            except Exception as e:
                raise FileOperationException(f"Failed to fetch chunk {chunk_id} from Discord: {str(e)}")
                
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    viewable_types = [
        'text/', 'image/', 'video/', 'audio/',
        'application/pdf',
        'application/json',
        'application/javascript',
        'application/xml'
    ]
    
    is_viewable = any(mime_type.startswith(vtype) for vtype in viewable_types)
    content_disposition = f"inline; filename={filename}" if is_viewable else f"attachment; filename={filename}"
    
    headers = {
        "Content-Type": mime_type,
        "Content-Disposition": content_disposition,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    return StreamingResponse(
        file_generator(),
        media_type=mime_type,
        headers=headers
    )