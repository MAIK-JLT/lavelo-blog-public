"""
Modelos SQLAlchemy para Lavelo Blog
Replica exacta de la estructura de Google Sheets
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Date
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Post(Base):
    """
    Modelo de Post del blog
    Replica exacta de las columnas A-AJ de Google Sheets
    """
    __tablename__ = 'posts'
    
    # COLUMNAS PRINCIPALES (A-H)
    codigo = Column(String(50), primary_key=True)  # C: Código Post
    fecha_programada = Column(Date)  # A: Fecha Programada
    hora_programada = Column(String(10))  # B: Hora Programada (HH:MM)
    titulo = Column(String(200))  # D: Título
    idea = Column(Text)  # E: Idea/Brief
    estado = Column(String(50), default='DRAFT')  # F: ESTADO
    drive_folder_id = Column(String(100))  # G: Drive Folder ID
    urls = Column(Text)  # H: URLs (separadas por comas)
    
    # TEXTOS - Checkboxes (I-O)
    base_txt = Column(Boolean, default=False)  # I: base.txt
    instagram_txt = Column(Boolean, default=False)  # J: instagram.txt
    linkedin_txt = Column(Boolean, default=False)  # K: linkedin.txt
    twitter_txt = Column(Boolean, default=False)  # L: twitter.txt
    facebook_txt = Column(Boolean, default=False)  # M: facebook.txt
    tiktok_txt = Column(Boolean, default=False)  # N: tiktok.txt
    prompt_imagen_base_txt = Column(Boolean, default=False)  # O: prompt_imagen_base.txt
    
    # IMÁGENES - Checkboxes (P-U)
    imagen_base_png = Column(Boolean, default=False)  # P: imagen_base.png
    instagram_1x1_png = Column(Boolean, default=False)  # Q: instagram_1x1.png
    instagram_stories_9x16_png = Column(Boolean, default=False)  # R: instagram_stories_9x16.png
    linkedin_16x9_png = Column(Boolean, default=False)  # S: linkedin_16x9.png
    twitter_16x9_png = Column(Boolean, default=False)  # T: twitter_16x9.png
    facebook_16x9_png = Column(Boolean, default=False)  # U: facebook_16x9.png
    
    # VIDEOS - Checkboxes (V-AA)
    script_video_base_txt = Column(Boolean, default=False)  # V: script_video_base.txt
    video_base_mp4 = Column(Boolean, default=False)  # W: video_base.mp4
    feed_16x9_mp4 = Column(Boolean, default=False)  # X: feed_16x9.mp4
    stories_9x16_mp4 = Column(Boolean, default=False)  # Y: stories_9x16.mp4
    shorts_9x16_mp4 = Column(Boolean, default=False)  # Z: shorts_9x16.mp4
    tiktok_9x16_mp4 = Column(Boolean, default=False)  # AA: tiktok_9x16.mp4
    
    # PUBLICACIÓN - Checkboxes (AB-AG)
    blog_published = Column(Boolean, default=False)  # AB: Blog
    instagram_published = Column(Boolean, default=False)  # AC: Instagram
    linkedin_published = Column(Boolean, default=False)  # AD: LinkedIn
    twitter_published = Column(Boolean, default=False)  # AE: Twitter
    facebook_published = Column(Boolean, default=False)  # AF: Facebook
    tiktok_published = Column(Boolean, default=False)  # AG: TikTok
    
    # CONTROL (AH-AJ)
    fecha_real_publicacion = Column(DateTime)  # AH: Fecha Real Publicación
    notas = Column(Text)  # AI: Notas/Errores
    feedback = Column(Text)  # AJ: Feedback
    
    # Metadata (no en Sheets)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario compatible con Sheets"""
        return {
            # Principales
            'codigo': self.codigo,
            'fecha_programada': self.fecha_programada.isoformat() if self.fecha_programada else None,
            'hora_programada': self.hora_programada,
            'titulo': self.titulo,
            'idea': self.idea,
            'estado': self.estado,
            'drive_folder_id': self.drive_folder_id,
            'urls': self.urls,
            
            # Textos
            'base_txt': self.base_txt,
            'instagram_txt': self.instagram_txt,
            'linkedin_txt': self.linkedin_txt,
            'twitter_txt': self.twitter_txt,
            'facebook_txt': self.facebook_txt,
            'tiktok_txt': self.tiktok_txt,
            'prompt_imagen_base_txt': self.prompt_imagen_base_txt,
            
            # Imágenes
            'imagen_base_png': self.imagen_base_png,
            'instagram_1x1_png': self.instagram_1x1_png,
            'instagram_stories_9x16_png': self.instagram_stories_9x16_png,
            'linkedin_16x9_png': self.linkedin_16x9_png,
            'twitter_16x9_png': self.twitter_16x9_png,
            'facebook_16x9_png': self.facebook_16x9_png,
            
            # Videos
            'script_video_base_txt': self.script_video_base_txt,
            'video_base_mp4': self.video_base_mp4,
            'feed_16x9_mp4': self.feed_16x9_mp4,
            'stories_9x16_mp4': self.stories_9x16_mp4,
            'shorts_9x16_mp4': self.shorts_9x16_mp4,
            'tiktok_9x16_mp4': self.tiktok_9x16_mp4,
            
            # Publicación
            'blog_published': self.blog_published,
            'instagram_published': self.instagram_published,
            'linkedin_published': self.linkedin_published,
            'twitter_published': self.twitter_published,
            'facebook_published': self.facebook_published,
            'tiktok_published': self.tiktok_published,
            
            # Control
            'fecha_real_publicacion': self.fecha_real_publicacion.isoformat() if self.fecha_real_publicacion else None,
            'notas': self.notas,
            'feedback': self.feedback,
            
            # Metadata
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class User(Base):
    """Modelo de Usuario (autenticación con Instagram/Facebook)"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instagram_id = Column(String(255), unique=True, nullable=True)  # ID único de Instagram
    instagram_username = Column(String(255))
    facebook_id = Column(String(255), unique=True, nullable=True)  # ID único de Facebook
    facebook_name = Column(String(255))
    
    # Tier y límites
    tier = Column(String(20), default='free')  # 'free', 'premium'
    posts_published_total = Column(Integer, default=0)  # Total de posts publicados
    
    # Stripe (para premium)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), nullable=True)  # 'active', 'canceled', 'past_due'
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'instagram_id': self.instagram_id,
            'instagram_username': self.instagram_username,
            'facebook_id': self.facebook_id,
            'facebook_name': self.facebook_name,
            'tier': self.tier,
            'posts_published_total': self.posts_published_total,
            'stripe_customer_id': self.stripe_customer_id,
            'subscription_status': self.subscription_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class AnonymousUsage(Base):
    """Modelo para tracking de usuarios anónimos por IP"""
    __tablename__ = 'anonymous_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False)  # IPv4 o IPv6
    posts_created_today = Column(Integer, default=0)
    last_post_date = Column(Date, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'posts_created_today': self.posts_created_today,
            'last_post_date': self.last_post_date.isoformat() if self.last_post_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SocialToken(Base):
    """Modelo de Tokens de Redes Sociales (por usuario)"""
    __tablename__ = 'social_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)  # Relación con User
    platform = Column(String(50), nullable=False)  # 'instagram', 'facebook', etc.
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)
    username = Column(String(100))
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'platform': self.platform,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'username': self.username,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }
