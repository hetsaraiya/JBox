# app/models.py
from sqlalchemy import Column, ForeignKey, Integer, String
from .database import Base

class FileChunk(Base):
    __tablename__ = "file_chunks"
    
    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    chunk_id = Column(Integer)
    discord_message_id = Column(String)
    folder_id = Column(Integer, ForeignKey("folders.id"))

class Folder(Base):
    __tablename__ = "folders"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
