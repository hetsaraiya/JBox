# app/routers/files.py
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.discord_bot import ensure_bot_ready, CHUNK_SIZE
from app.database import get_db, AsyncSessionLocal
from app.discord_bot import bot, StorageBot
from app.models import FileChunk
from app.logger import logger
from app.utils.auth import get_current_active_user
from app.exceptions import (
    NotFoundException, DatabaseException, FileOperationException,
    DiscordBotException, ValidationException
)

router = APIRouter(tags=["files"])

@router.post("/upload/")
async def upload_file(file: UploadFile, folder_id: int, current_user = Depends(get_current_active_user)):
    uploaded_chunks = []
    try:
        channel = await ensure_bot_ready()
        if not channel:
            raise DiscordBotException("Discord channel not available")
        
        async with AsyncSessionLocal() as db:
            # Verify folder belongs to current user
            result = await db.execute(
                text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
                {"folder_id": folder_id, "user_id": current_user.id}
            )
            folder = result.fetchone()
            if not folder:
                raise NotFoundException(f"Folder with id {folder_id} not found or does not belong to you")
            
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
                try:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    chunk_id += 1
                    total_size += len(chunk)
                    message_id = await bot.upload_chunk(chunk, file.filename, chunk_id)

                    chunk_entry = FileChunk(
                        file_name=file.filename,
                        chunk_id=chunk_id,
                        discord_message_id=message_id,
                        folder_id=folder_id
                    )
                    db.add(chunk_entry)
                    uploaded_chunks.append(chunk_entry)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error uploading chunk {chunk_id}: {str(e)}")

            await db.commit()
            
            logger.info(f"User {current_user.username} uploaded file {file.filename} to folder {folder_id}")
            
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "chunks": chunk_id
        }
    
    except Exception as e:
        logger.error(f"Error during file upload by user {current_user.username}: {str(e)}")
        async with AsyncSessionLocal() as db:
            for chunk_entry in uploaded_chunks:
                try:
                    await db.execute(text("DELETE FROM file_chunks WHERE file_name = :file_name AND chunk_id = :chunk_id AND folder_id = :folder_id"), {"file_name": chunk_entry.file_name, "chunk_id": chunk_entry.chunk_id, "folder_id": chunk_entry.folder_id})
                except Exception as db_error:
                    raise HTTPException(status_code=500, detail=f"Error deleting chunk {chunk_entry.chunk_id}: {str(db_error)}")
            await db.commit()
        channel = await ensure_bot_ready()
        if channel:
            for chunk_entry in uploaded_chunks:
                try:
                    message = await channel.fetch_message(chunk_entry.discord_message_id)
                    await message.delete()
                except Exception as e:
                    logger.error(f"Failed to delete message {chunk_entry.discord_message_id}: {e}")
        raise FileOperationException(f"Error uploading file: {str(e)}")

@router.delete("/files/{file_name}")
async def delete_file(file_name: str, folder_id: int, current_user = Depends(get_current_active_user)):
    try:
        async with AsyncSessionLocal() as db:
            # Verify folder belongs to current user
            result = await db.execute(
                text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
                {"folder_id": folder_id, "user_id": current_user.id}
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
                    except Exception as e:
                        logger.error(f"Failed to delete message {chunk.discord_message_id}: {e}")
            
            logger.info(f"User {current_user.username} deleted file {file_name} from folder {folder_id}")
            
            return {"message": f"File '{file_name}' deleted successfully"}
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/files/{folder_id}")
async def list_files(folder_id: int, current_user = Depends(get_current_active_user)):
    try:    
        async with AsyncSessionLocal() as db:
            # Verify folder belongs to current user
            result = await db.execute(
                text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
                {"folder_id": folder_id, "user_id": current_user.id}
            )
            folder = result.fetchone()
            if not folder:
                raise NotFoundException(f"Folder with id {folder_id} not found or does not belong to you")
                
            result = await db.execute(
                text("SELECT DISTINCT file_name FROM file_chunks WHERE folder_id = :folder_id"),
                {"folder_id": folder_id}
            )
            files = result.fetchall()
            response = [{"name": f[0]} for f in files]
            
            logger.info(f"User {current_user.username} listed files in folder {folder_id}")
            
            return response
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error listing files.")

@router.get("/download/{filename}")
async def download_file(filename: str, folder_id: int, current_user = Depends(get_current_active_user)):
    try:
        async with AsyncSessionLocal() as db:
            # Verify folder belongs to current user
            result = await db.execute(
                text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
                {"folder_id": folder_id, "user_id": current_user.id}
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
            
            async def file_generator():
                for chunk_id, discord_message_id in chunks:
                    try:
                        message = await bot.channel.fetch_message(discord_message_id)
                        attachment = message.attachments[0]
                        chunk = await attachment.read()
                        yield chunk
                    except Exception as e:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to fetch chunk {chunk_id} from Discord: {str(e)}"
                        )
                        
            logger.info(f"User {current_user.username} downloaded file {filename} from folder {folder_id}")
            
            return StreamingResponse(file_generator(), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise FileOperationException(f"Error downloading file: {str(e)}")  

import mimetypes

@router.get("/open/{name}")
async def open_file(name: str, folder_id: int, current_user = Depends(get_current_active_user)):
    try:
        async with AsyncSessionLocal() as db:
            # Verify folder belongs to current user
            result = await db.execute(
                text("SELECT id FROM folders WHERE id = :folder_id AND user_id = :user_id"),
                {"folder_id": folder_id, "user_id": current_user.id}
            )
            folder = result.fetchone()
            if not folder:
                raise NotFoundException(f"Folder with id {folder_id} not found or does not belong to you")
                
            result = await db.execute(
                text("SELECT file_name, chunk_id, discord_message_id FROM file_chunks WHERE file_name = :name AND folder_id = :folder_id ORDER BY chunk_id"),
                {"name": name, "folder_id": folder_id}
            )
            chunks = result.fetchall()
            
            if not chunks:
                raise HTTPException(
                    status_code=404,
                    detail=f"File '{name}' not found"
                )
            
            mime_type, _ = mimetypes.guess_type(name)
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
            
            async def file_generator():
                for _, chunk_id, discord_message_id in chunks:
                    try:
                        message = await bot.channel.fetch_message(discord_message_id)
                        attachment = message.attachments[0]
                        chunk = await attachment.read()
                        yield chunk
                    except Exception as e:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to fetch chunk {chunk_id} from Discord: {str(e)}"
                        )

            content_disposition = f"inline; filename={name}" if is_viewable else f"attachment; filename={name}"
            
            headers = {
                "Content-Type": mime_type,
                "Content-Disposition": content_disposition,
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
            
            logger.info(f"User {current_user.username} opened file {name} from folder {folder_id}")
            
            return StreamingResponse(
                file_generator(),
                media_type=mime_type,
                headers=headers
            )
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error opening file: {str(e)}")


@router.get("/view/{id}")
async def view_file(id: int, current_user = Depends(get_current_active_user)):
    try:
        async with AsyncSessionLocal() as db:
            # Get file info and verify ownership
            result = await db.execute(
                text("""
                    SELECT fc.file_name, fc.chunk_id, fc.discord_message_id, f.user_id 
                    FROM file_chunks fc 
                    JOIN folders f ON fc.folder_id = f.id 
                    WHERE fc.id = :id
                """),
                {"id": id}
            )
            chunk = result.fetchone()
            
            if not chunk:
                raise HTTPException(
                    status_code=404,
                    detail=f"File with id {id} not found"
                )
                
            # Check if file belongs to current user
            if chunk.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this file"
                )
                
            filename = chunk.file_name
            
            # Get all chunks of the file
            result = await db.execute(
                text("""
                    SELECT fc.file_name, fc.chunk_id, fc.discord_message_id 
                    FROM file_chunks fc 
                    JOIN folders f ON fc.folder_id = f.id 
                    WHERE fc.file_name = :filename AND f.user_id = :user_id
                    ORDER BY fc.chunk_id
                """),
                {"filename": filename, "user_id": current_user.id}
            )
            chunks = result.fetchall()
            
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            async def file_generator():
                for _, chunk_id, discord_message_id in chunks:
                    try:
                        message = await bot.channel.fetch_message(discord_message_id)
                        attachment = message.attachments[0]
                        chunk = await attachment.read()
                        yield chunk
                    except Exception as e:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to fetch chunk {chunk_id} from Discord: {str(e)}"
                        )
            
            logger.info(f"User {current_user.username} viewed file {filename}")
            
            headers = {"Content-Disposition": f"inline; filename={filename}"}
            return StreamingResponse(file_generator(), media_type=mime_type, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error viewing file: {str(e)}")