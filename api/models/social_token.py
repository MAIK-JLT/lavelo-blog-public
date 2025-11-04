from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SocialTokenBase(BaseModel):
    """Modelo base de Token de Red Social"""
    platform: str = Field(..., min_length=1, max_length=50)
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    username: Optional[str] = None

class SocialTokenCreate(SocialTokenBase):
    """Modelo para crear un token"""
    pass

class SocialTokenUpdate(BaseModel):
    """Modelo para actualizar un token (todos los campos opcionales)"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    username: Optional[str] = None
    last_used: Optional[datetime] = None

class SocialToken(SocialTokenBase):
    """Modelo completo de Token (respuesta)"""
    connected_at: datetime
    last_used: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Para convertir desde dict/SQLAlchemy
