# app/routers/files.py
from fastapi import APIRouter, UploadFile, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..discord_bot import ensure_bot_ready, CHUNK_SIZE
from ..database import get_db, AsyncSessionLocal
from ..discord_bot import bot, StorageBot
from ..models import FileChunk
from sqlalchemy import text
from ..websocket_manager import manager

router = APIRouter(tags=["files"])

@router.post("/upload/")
async def upload_file(file: UploadFile, folder_id: int):
    try:
        channel = await ensure_bot_ready()
        if not channel:
            raise HTTPException(
                status_code=503,
                detail="Discord channel not available. Please check configuration."
            )
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT id FROM folders WHERE id = :name"),
                {"name": folder_id}
            )
            folder = result.fetchone()
            if not folder:
                raise HTTPException(
                    status_code=404,
                    detail=f"Folder '{folder_id}' not found"
                )
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
            uploaded_chunks = []
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                chunk_id += 1
                total_size += len(chunk)
                message_id = await bot.upload_chunk(chunk, file.filename, chunk_id)
                await manager.send_message(f"Uploaded {total_size} bytes")
                chunk_entry = FileChunk(
                    file_name=file.filename,
                    chunk_id=chunk_id,
                    discord_message_id=message_id,
                    folder_id=folder_id
                )
                db.add(chunk_entry)
                uploaded_chunks.append(chunk_entry)
                await manager.send_message(f"Uploaded {total_size} bytes")
            await db.commit()
        await manager.send_message("Upload complete")
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "chunks": chunk_id
        }
    except Exception as e:
        await manager.send_message(f"Error: {str(e)}")
        # Rollback the database entries and delete uploaded chunks from Discord
        async with AsyncSessionLocal() as db:
            for chunk_entry in uploaded_chunks:
                await db.execute(
                    text("DELETE FROM file_chunks WHERE file_name = :file_name AND chunk_id = :chunk_id AND folder_id = :folder_id"),
                    {"file_name": chunk_entry.file_name, "chunk_id": chunk_entry.chunk_id, "folder_id": chunk_entry.folder_id}
                )
            await db.commit()
        channel = await ensure_bot_ready()
        if channel:
            for chunk_entry in uploaded_chunks:
                try:
                    message = await channel.fetch_message(chunk_entry.discord_message_id)
                    await message.delete()
                except Exception as e:
                    print(f"Failed to delete message {chunk_entry.discord_message_id}: {e}")
        return {"status": "error", "message": str(e)}

@router.delete("/files/{file_name}")
async def delete_file(file_name: str, folder_name: int):
    async with AsyncSessionLocal() as db:
        folder_id = folder_name
        result = await db.execute(
            text("SELECT discord_message_id FROM file_chunks WHERE file_name = :file_name AND folder_id = :folder_id"),
            {"file_name": file_name, "folder_id": folder_id}
        )
        file_chunks = result.fetchall()
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
                    print(f"Failed to delete message {chunk.discord_message_id}: {e}")
        
        return {"message": f"File '{file_name}' deleted successfully"}

@router.get("/files/{folder_id}")
async def list_files(folder_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT DISTINCT file_name FROM file_chunks WHERE folder_id = :folder_id"),
            {"folder_id": folder_id}
        )
        files = result.fetchall()
        response = [{"name": f[0]} for f in files]
        return response

@router.get("/download/{filename}")
async def download_file(filename: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT chunk_id, discord_message_id FROM file_chunks WHERE file_name = :filename ORDER BY chunk_id"),
            {"filename": filename}
        )
        chunks = result.fetchall()
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"File {filename} not found"
            )
        
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
        
        return StreamingResponse(file_generator(), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={filename}"})

import mimetypes

@router.get("/open/{id}")
async def open_file(id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT file_name, chunk_id, discord_message_id FROM file_chunks WHERE id = :id ORDER BY chunk_id"),
            {"id": id}
        )
        chunks = result.fetchall()
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"File with id {id} not found"
            )
        
        filename = chunks[0][0]
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
        
        return StreamingResponse(file_generator(), media_type=mime_type)

@router.get("/view/{id}")
async def view_file(id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT file_name, chunk_id, discord_message_id FROM file_chunks WHERE id = :id ORDER BY chunk_id"),
            {"id": id}
        )
        chunks = result.fetchall()
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"File with id {id} not found"
            )
        
        filename = chunks[0][0]
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
        
        headers = {"Content-Disposition": f"inline; filename={filename}"}
        return StreamingResponse(file_generator(), media_type=mime_type, headers=headers)