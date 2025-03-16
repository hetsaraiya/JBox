from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Tuple
from fastapi import status

from app.exceptions import NotFoundException, DatabaseException, FileOperationException
from app.utils.constants import FILE_NOT_FOUND, INVALID_FILE_TYPE, FILE_TYPE_NOT_SUPPORTED
from app.models import FileChunk
import mimetypes
import os

# This will be replaced with the modularized Discord bot in discord_service.py
from app.services.discord_service import bot, ensure_bot_ready

# Enhanced list of viewable MIME type categories
VIEWABLE_MIME_TYPES = [
    'text/',
    'image/',
    'video/',
    'audio/',
    'application/pdf',
    'application/json',
    'application/javascript',
    'application/xml',
    'application/xhtml+xml'
]

# Map of specific file extensions to MIME types (for better detection)
EXTENSION_MIME_MAP = {
    '.md': 'text/markdown',
    '.svg': 'image/svg+xml',
    '.yaml': 'text/yaml',
    '.yml': 'text/yaml',
    '.csv': 'text/csv',
    '.py': 'text/x-python',
    '.js': 'application/javascript',
    '.ts': 'text/typescript',
    '.jsx': 'text/jsx',
    '.tsx': 'text/tsx',
    '.json': 'application/json',
}

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
        
        # Enhanced file list with more info
        file_list = []
        for f in files:
            name = f[0]
            mime_type = get_mime_type(name)
            is_viewable = is_file_viewable(mime_type)
            file_list.append({
                "name": name,
                "mime_type": mime_type,
                "viewable": is_viewable,
                "type": get_file_type_category(mime_type)
            })
        
        return file_list
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

def get_mime_type(filename: str) -> str:
    """Get the MIME type of a file with enhanced detection."""
    mime_type, _ = mimetypes.guess_type(filename)
    
    if not mime_type:
        # Try to determine MIME type from extension
        _, ext = os.path.splitext(filename.lower())
        if ext in EXTENSION_MIME_MAP:
            mime_type = EXTENSION_MIME_MAP[ext]
        else:
            mime_type = "application/octet-stream"
            
    return mime_type

def is_file_viewable(mime_type: str) -> bool:
    """Determine if a file type is viewable in browser."""
    return any(mime_type.startswith(vtype) for vtype in VIEWABLE_MIME_TYPES)

def get_file_type_category(mime_type: str) -> str:
    """Get the general category of a file based on MIME type."""
    if mime_type.startswith('image/'):
        return "image"
    elif mime_type.startswith('video/'):
        return "video"
    elif mime_type.startswith('audio/'):
        return "audio"
    elif mime_type.startswith('text/'):
        return "text"
    elif mime_type == 'application/pdf':
        return "pdf"
    elif mime_type in ['application/json', 'application/javascript', 'application/xml']:
        return "code"
    else:
        return "other"

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
                
    mime_type = get_mime_type(filename)
        
    return StreamingResponse(
        file_generator(), 
        media_type=mime_type, 
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": mime_type,
            "X-File-Name": filename,
            "X-File-Type": mime_type,
            "Cache-Control": "no-cache"
        }
    )

async def create_file_view_stream(filename: str, chunks):
    """Create a streaming response for viewing a file with enhanced frontend support."""
    async def file_generator():
        for chunk_id, discord_message_id in chunks:
            try:
                message = await bot.channel.fetch_message(discord_message_id)
                attachment = message.attachments[0]
                chunk = await attachment.read()
                yield chunk
            except Exception as e:
                raise FileOperationException(f"Failed to fetch chunk {chunk_id} from Discord: {str(e)}")
    
    # Get MIME type and check if viewable
    mime_type = get_mime_type(filename)
    is_viewable = is_file_viewable(mime_type)
    file_type = get_file_type_category(mime_type)
    
    # If not viewable, return a structured error response or force download
    if not is_viewable:
        # Option 1: Return a JSON response with error info
        if file_type == "other":
            # Return a structured response with file metadata
            response_headers = {
                "Content-Type": "application/json",
                "X-File-Name": filename,
                "X-File-Type": mime_type,
                "X-File-Viewable": "false",
                "X-File-Category": file_type,
                "Cache-Control": "no-cache"
            }
            
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={
                    "status": False,
                    "message": FILE_TYPE_NOT_SUPPORTED,
                    "error": f"File type {mime_type} is not supported for viewing in browser",
                    "file": {
                        "name": filename,
                        "type": mime_type,
                        "category": file_type,
                        "viewable": False
                    },
                    "recommended_action": "download"
                },
                headers=response_headers
            )
    
    # For viewable files, set appropriate headers
    content_disposition = "inline" if is_viewable else "attachment"
    
    headers = {
        "Content-Type": mime_type,
        "Content-Disposition": f"{content_disposition}; filename={filename}",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "X-File-Name": filename,
        "X-File-Type": mime_type,
        "X-File-Viewable": str(is_viewable).lower(),
        "X-File-Category": file_type,
        "Cache-Control": "no-cache"
    }
    
    return StreamingResponse(
        file_generator(),
        media_type=mime_type,
        headers=headers
    )

async def get_file_metadata(db: AsyncSession, filename: str, folder_id: int, user_id: int) -> Dict[str, Any]:
    """Get metadata about a file without retrieving its contents."""
    # Verify the file exists and belongs to the user
    result = await db.execute(
        text("""
            SELECT COUNT(*) as chunk_count 
            FROM file_chunks 
            WHERE file_name = :filename AND folder_id = :folder_id
        """),
        {"filename": filename, "folder_id": folder_id}
    )
    file_info = result.fetchone()
    
    if not file_info or file_info.chunk_count == 0:
        raise NotFoundException(f"File {filename} not found in folder {folder_id}")
        
    # Get file metadata
    mime_type = get_mime_type(filename)
    is_viewable = is_file_viewable(mime_type)
    file_type = get_file_type_category(mime_type)
    
    return {
        "name": filename,
        "mime_type": mime_type,
        "viewable": is_viewable,
        "type": file_type,
        "chunk_count": file_info.chunk_count
    }