# app/routers/folders.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi.templating import Jinja2Templates
from ..database import get_db
from ..models import Folder

router = APIRouter(tags=["folders"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/create_folder/")
async def create_folder(name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT name FROM folders WHERE name LIKE :name"), {"name": f"{name}%"})
    existing_folders = result.fetchall()
    
    if existing_folders:
        name = f"{name}_{len(existing_folders) + 1}"
    
    new_folder = Folder(name=name)
    db.add(new_folder)
    await db.commit()
    return {"message": f"Folder '{name}' created successfully"}

@router.delete("/folders/{folder_name}")
async def delete_folder(folder_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT id FROM folders WHERE name = :name"), {"name": folder_name})
    folder = result.fetchone()
    
    if not folder:
        raise HTTPException(status_code=404, detail=f"Folder '{folder_name}' not found")
    
    folder_id = folder.id
    
    await db.execute(text("DELETE FROM file_chunks WHERE folder_id = :folder_id"), {"folder_id": folder_id})
    await db.execute(text("DELETE FROM folders WHERE id = :id"), {"id": folder_id})
    await db.commit()
    
    return {"message": f"Folder '{folder_name}' and all its files deleted successfully"}

@router.get("/folders/")
async def list_folders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT id, name FROM folders"))
    folders = result.fetchall()
    return [{"id": folder.id, "name": folder.name} for folder in folders]

# @router.get("/files/{folder_id}")
# async def list_files(folder_id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(text("SELECT name FROM files WHERE folder_id = :folder_id"), {"folder_id": folder_id})
#     files = result.fetchall()
#     return [{"name": file.name} for file in files]

@router.get("/folder/")
async def get_folder_page(request: Request):
    return templates.TemplateResponse("folder.html", {"request": request})
