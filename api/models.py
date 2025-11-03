"""
Modelos SQLAlchemy para Lavelo Blog
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Post(Base):
    """Modelo de Post del blog"""
    __tablename__ = 'posts'
    
    codigo = Column(String(50), primary_key=True)
    titulo = Column(String(200), nullable=False)
    contenido = Column(Text)
    categoria = Column(String(50), default='training')
    estado = Column(String(50), default='DRAFT')
    drive_folder_id = Column(String(100))
    fecha_programada = Column(DateTime)
    hora_programada = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'codigo': self.codigo,
            'titulo': self.titulo,
            'contenido': self.contenido,
            'categoria': self.categoria,
            'estado': self.estado,
            'drive_folder_id': self.drive_folder_id,
            'fecha_programada': self.fecha_programada.isoformat() if self.fecha_programada else None,
            'hora_programada': self.hora_programada,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SocialToken(Base):
    """Modelo de Tokens de Redes Sociales"""
    __tablename__ = 'social_tokens'
    
    platform = Column(String(50), primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)
    username = Column(String(100))
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'platform': self.platform,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'username': self.username,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }
