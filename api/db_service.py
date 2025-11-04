#!/usr/bin/env python3
"""
Servicio de base de datos MySQL para reemplazar sheets_service.py
Proporciona las mismas funciones pero usando MySQL en lugar de Google Sheets
"""
from database import SessionLocal
from db_models import Post, SocialToken
from datetime import datetime
from typing import List, Dict, Optional

def get_all_posts() -> List[Dict]:
    """Obtiene todos los posts de MySQL"""
    db = SessionLocal()
    try:
        posts = db.query(Post).all()
        return [post.to_dict() for post in posts]
    finally:
        db.close()

def get_post_by_codigo(codigo: str) -> Optional[Dict]:
    """Obtiene un post por su código"""
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.codigo == codigo).first()
        return post.to_dict() if post else None
    finally:
        db.close()

def create_post(data: Dict) -> Dict:
    """Crea un nuevo post en MySQL"""
    db = SessionLocal()
    try:
        # Parsear fecha si viene como string
        fecha_prog = None
        if data.get('fecha_programada'):
            if isinstance(data['fecha_programada'], str):
                try:
                    fecha_prog = datetime.strptime(data['fecha_programada'], '%Y-%m-%d').date()
                except:
                    pass
            else:
                fecha_prog = data['fecha_programada']
        
        post = Post(
            codigo=data['codigo'],
            fecha_programada=fecha_prog,
            hora_programada=data.get('hora_programada'),
            titulo=data.get('titulo', ''),
            idea=data.get('idea', ''),
            estado=data.get('estado', 'DRAFT'),
            drive_folder_id=data.get('drive_folder_id'),
            urls=data.get('urls')
        )
        
        db.add(post)
        db.commit()
        db.refresh(post)
        
        return post.to_dict()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def update_post(codigo: str, data: Dict) -> Dict:
    """Actualiza un post existente"""
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.codigo == codigo).first()
        
        if not post:
            raise ValueError(f"Post {codigo} no encontrado")
        
        # Actualizar campos básicos
        if 'titulo' in data:
            post.titulo = data['titulo']
        if 'idea' in data:
            post.idea = data['idea']
        if 'estado' in data:
            post.estado = data['estado']
        if 'drive_folder_id' in data:
            post.drive_folder_id = data['drive_folder_id']
        if 'urls' in data:
            post.urls = data['urls']
        if 'hora_programada' in data:
            post.hora_programada = data['hora_programada']
        if 'notas' in data:
            post.notas = data['notas']
        if 'feedback' in data:
            post.feedback = data['feedback']
        
        # Actualizar fecha programada
        if 'fecha_programada' in data:
            if isinstance(data['fecha_programada'], str):
                try:
                    post.fecha_programada = datetime.strptime(data['fecha_programada'], '%Y-%m-%d').date()
                except:
                    pass
            else:
                post.fecha_programada = data['fecha_programada']
        
        # Actualizar checkboxes de textos
        if 'base_txt' in data:
            post.base_txt = data['base_txt']
        if 'instagram_txt' in data:
            post.instagram_txt = data['instagram_txt']
        if 'linkedin_txt' in data:
            post.linkedin_txt = data['linkedin_txt']
        if 'twitter_txt' in data:
            post.twitter_txt = data['twitter_txt']
        if 'facebook_txt' in data:
            post.facebook_txt = data['facebook_txt']
        if 'tiktok_txt' in data:
            post.tiktok_txt = data['tiktok_txt']
        if 'prompt_imagen_base_txt' in data:
            post.prompt_imagen_base_txt = data['prompt_imagen_base_txt']
        
        # Actualizar checkboxes de imágenes
        if 'imagen_base_png' in data:
            post.imagen_base_png = data['imagen_base_png']
        if 'instagram_1x1_png' in data:
            post.instagram_1x1_png = data['instagram_1x1_png']
        if 'instagram_stories_9x16_png' in data:
            post.instagram_stories_9x16_png = data['instagram_stories_9x16_png']
        if 'linkedin_16x9_png' in data:
            post.linkedin_16x9_png = data['linkedin_16x9_png']
        if 'twitter_16x9_png' in data:
            post.twitter_16x9_png = data['twitter_16x9_png']
        if 'facebook_16x9_png' in data:
            post.facebook_16x9_png = data['facebook_16x9_png']
        
        # Actualizar checkboxes de videos
        if 'script_video_base_txt' in data:
            post.script_video_base_txt = data['script_video_base_txt']
        if 'video_base_mp4' in data:
            post.video_base_mp4 = data['video_base_mp4']
        if 'feed_16x9_mp4' in data:
            post.feed_16x9_mp4 = data['feed_16x9_mp4']
        if 'stories_9x16_mp4' in data:
            post.stories_9x16_mp4 = data['stories_9x16_mp4']
        if 'shorts_9x16_mp4' in data:
            post.shorts_9x16_mp4 = data['shorts_9x16_mp4']
        if 'tiktok_9x16_mp4' in data:
            post.tiktok_9x16_mp4 = data['tiktok_9x16_mp4']
        
        # Actualizar checkboxes de publicación
        if 'blog_published' in data:
            post.blog_published = data['blog_published']
        if 'instagram_published' in data:
            post.instagram_published = data['instagram_published']
        if 'linkedin_published' in data:
            post.linkedin_published = data['linkedin_published']
        if 'twitter_published' in data:
            post.twitter_published = data['twitter_published']
        if 'facebook_published' in data:
            post.facebook_published = data['facebook_published']
        if 'tiktok_published' in data:
            post.tiktok_published = data['tiktok_published']
        
        # Actualizar fecha real de publicación
        if 'fecha_real_publicacion' in data:
            if isinstance(data['fecha_real_publicacion'], str):
                try:
                    post.fecha_real_publicacion = datetime.fromisoformat(data['fecha_real_publicacion'])
                except:
                    pass
            else:
                post.fecha_real_publicacion = data['fecha_real_publicacion']
        
        db.commit()
        db.refresh(post)
        
        return post.to_dict()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def delete_post(codigo: str) -> bool:
    """Elimina un post"""
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.codigo == codigo).first()
        
        if not post:
            return False
        
        db.delete(post)
        db.commit()
        
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_social_token(platform: str) -> Optional[Dict]:
    """Obtiene el token de una red social"""
    db = SessionLocal()
    try:
        token = db.query(SocialToken).filter(SocialToken.platform == platform).first()
        
        if not token:
            return None
        
        return {
            'platform': token.platform,
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'expires_at': token.expires_at.isoformat() if token.expires_at else None,
            'username': token.username
        }
    finally:
        db.close()

def get_all_social_tokens() -> List[Dict]:
    """Obtiene todos los tokens de redes sociales"""
    db = SessionLocal()
    try:
        tokens = db.query(SocialToken).all()
        
        return [{
            'platform': token.platform,
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'expires_at': token.expires_at.isoformat() if token.expires_at else None,
            'username': token.username
        } for token in tokens]
    finally:
        db.close()

def save_social_token(platform: str, access_token: str, refresh_token: str = None, 
                     expires_at: datetime = None, username: str = None) -> Dict:
    """Guarda o actualiza un token de red social"""
    db = SessionLocal()
    try:
        token = db.query(SocialToken).filter(SocialToken.platform == platform).first()
        
        if token:
            # Actualizar existente
            token.access_token = access_token
            if refresh_token is not None:
                token.refresh_token = refresh_token
            if expires_at is not None:
                token.expires_at = expires_at
            if username is not None:
                token.username = username
        else:
            # Crear nuevo
            token = SocialToken(
                platform=platform,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                username=username
            )
            db.add(token)
        
        db.commit()
        db.refresh(token)
        
        return {
            'platform': token.platform,
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'expires_at': token.expires_at.isoformat() if token.expires_at else None,
            'username': token.username
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def delete_social_token(platform: str) -> bool:
    """Elimina un token de red social"""
    db = SessionLocal()
    try:
        token = db.query(SocialToken).filter(SocialToken.platform == platform).first()
        
        if not token:
            return False
        
        db.delete(token)
        db.commit()
        
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
