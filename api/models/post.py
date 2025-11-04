from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PostBase(BaseModel):
    """Modelo base de Post"""
    titulo: str = Field(..., min_length=1, max_length=200)
    categoria: Optional[str] = None
    idea: Optional[str] = None

class PostCreate(PostBase):
    """Modelo para crear un post"""
    fecha_programada: Optional[datetime] = None
    hora_programada: Optional[str] = None

class PostUpdate(BaseModel):
    """Modelo para actualizar un post (todos los campos opcionales)"""
    titulo: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[str] = None
    idea: Optional[str] = None
    drive_folder_id: Optional[str] = None
    
    # Checkboxes de textos
    base_txt: Optional[bool] = None
    instagram_txt: Optional[bool] = None
    linkedin_txt: Optional[bool] = None
    twitter_txt: Optional[bool] = None
    facebook_txt: Optional[bool] = None
    tiktok_txt: Optional[bool] = None
    prompt_imagen_txt: Optional[bool] = None
    
    # Checkboxes de imágenes
    imagen_base: Optional[bool] = None
    instagram_image: Optional[bool] = None
    instagram_stories: Optional[bool] = None
    linkedin_image: Optional[bool] = None
    twitter_image: Optional[bool] = None
    facebook_image: Optional[bool] = None
    
    # Checkboxes de videos
    script_video_txt: Optional[bool] = None
    video_base: Optional[bool] = None
    feed_video: Optional[bool] = None
    stories_video: Optional[bool] = None
    shorts_video: Optional[bool] = None
    tiktok_video: Optional[bool] = None

class Post(PostBase):
    """Modelo completo de Post (respuesta)"""
    id: int
    codigo: str
    estado: str
    drive_folder_id: Optional[str] = None
    fecha_programada: Optional[datetime] = None
    hora_programada: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Checkboxes
    base_txt: bool = False
    instagram_txt: bool = False
    linkedin_txt: bool = False
    twitter_txt: bool = False
    facebook_txt: bool = False
    tiktok_txt: bool = False
    prompt_imagen_txt: bool = False
    imagen_base: bool = False
    instagram_image: bool = False
    instagram_stories: bool = False
    linkedin_image: bool = False
    twitter_image: bool = False
    facebook_image: bool = False
    script_video_txt: bool = False
    video_base: bool = False
    feed_video: bool = False
    stories_video: bool = False
    shorts_video: bool = False
    tiktok_video: bool = False
    
    class Config:
        from_attributes = True  # Para convertir desde dict/SQLAlchemy
