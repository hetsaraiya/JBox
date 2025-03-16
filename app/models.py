# app/models.py
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    folders = relationship("Folder", back_populates="owner", cascade="all, delete-orphan")

class FileChunk(Base):
    __tablename__ = "file_chunks"
    
    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    chunk_id = Column(Integer)
    discord_message_id = Column(String)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    
    # Relationship with Folder
    folder = relationship("Folder", back_populates="file_chunks")

class Folder(Base):
    __tablename__ = "folders"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    owner = relationship("User", back_populates="folders")
    file_chunks = relationship("FileChunk", back_populates="folder", cascade="all, delete-orphan")
    
    # Folder name is unique per user
    __table_args__ = (
        # SQLAlchemy constraint for unique folder name per user
        {"sqlite_autoincrement": True},
    )
