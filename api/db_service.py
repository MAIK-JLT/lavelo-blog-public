#!/usr/bin/env python3
"""
Servicio de base de datos MySQL para reemplazar sheets_service.py
Proporciona las mismas funciones pero usando MySQL en lugar de Google Sheets
"""
from database import SessionLocal
from db_models import Post, SocialToken, SocialPage
from datetime import datetime, timedelta
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
            'username': token.username,
            'page_id': token.page_id,
            'instagram_account_id': token.instagram_account_id
        } for token in tokens]
    finally:
        db.close()

def save_social_token(platform: str, token_data: Dict = None,
                       access_token: str = None,
                       refresh_token: str = None,
                       expires_at: datetime = None,
                       username: str = None,
                       page_id: str = None,
                       instagram_account_id: str = None) -> Dict:
    """
    Guarda o actualiza un token de red social.
    """
    db = SessionLocal()
    try:
        # NORMALIZAR token_data
        if token_data:
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            username = token_data.get('username')
            page_id = token_data.get('page_id')
            instagram_account_id = token_data.get('instagram_account_id')
            user_id = token_data.get('user_id')

            # Calcular expires_at
            expires_in = token_data.get('expires_in')
            if expires_in:
                expires_at = datetime.now() + timedelta(seconds=int(expires_in))
            elif isinstance(token_data.get('expires_at'), str):
                expires_at = datetime.fromisoformat(token_data.get('expires_at'))

        # --- GUARDAR (por plataforma y usuario) ---
        # Nota: SocialToken.user_id es NOT NULL, por lo que debemos persistirlo siempre
        rec = None
        if token_data and user_id is not None:
            rec = db.query(SocialToken).filter(
                SocialToken.platform == platform,
                SocialToken.user_id == user_id
            ).first()
        else:
            # Compatibilidad legacy (sin user_id)
            rec = db.query(SocialToken).filter(SocialToken.platform == platform).first()

        if rec:
            rec.access_token = access_token or rec.access_token
            rec.refresh_token = refresh_token or rec.refresh_token
            rec.expires_at = expires_at or rec.expires_at
            rec.username = username or rec.username
            rec.page_id = page_id or rec.page_id
            rec.instagram_account_id = instagram_account_id or rec.instagram_account_id
            if token_data and user_id is not None:
                rec.user_id = rec.user_id or user_id
        else:
            rec = SocialToken(
                platform=platform,
                access_token=access_token,
                refresh_token=refresh_token,
                username=username,
                expires_at=expires_at,
                page_id=page_id,
                instagram_account_id=instagram_account_id,
                user_id=user_id if token_data else None
            )
            db.add(rec)

        db.commit()
        db.refresh(rec)

        return rec.to_dict()

    except Exception as e:
        db.rollback()
        print(f"❌ Error guardando token: {e}")
        raise
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

def get_social_tokens() -> Dict:
    """Obtiene todos los tokens organizados por plataforma"""
    tokens_list = get_all_social_tokens()
    tokens_dict = {}
    
    for token in tokens_list:
        platform = token['platform']
        tokens_dict[platform] = {
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'expires_at': token['expires_at'],
            'username': token['username'],
            'connected_at': token.get('connected_at'),
            'last_used': token.get('last_used'),
            'page_id': token.get('page_id'),
            'instagram_account_id': token.get('instagram_account_id')
        }
    
    return tokens_dict

# ==============================
# Social Pages (Facebook/IG)
# ==============================
def upsert_social_page(page: Dict) -> Dict:
    """
    Crea o actualiza una página social (por page_id).
    page = {
        'platform': 'facebook',
        'page_id': '123',
        'page_name': 'Mi página',
        'instagram_account_id': '1789...',
        'page_access_token': 'EAA....',
        'expires_at': datetime | None,
        'user_id': int | None
    }
    """
    db = SessionLocal()
    try:
        rec = db.query(SocialPage).filter(SocialPage.page_id == page['page_id']).first()

        if rec:
            rec.platform = page.get('platform', rec.platform)
            rec.page_name = page.get('page_name', rec.page_name)
            rec.instagram_account_id = page.get('instagram_account_id', rec.instagram_account_id)
            rec.page_access_token = page.get('page_access_token', rec.page_access_token)
            rec.expires_at = page.get('expires_at', rec.expires_at)
            rec.user_id = page.get('user_id', rec.user_id)
        else:
            rec = SocialPage(
                platform=page.get('platform', 'facebook'),
                page_id=page['page_id'],
                page_name=page.get('page_name'),
                instagram_account_id=page.get('instagram_account_id'),
                page_access_token=page.get('page_access_token'),
                expires_at=page.get('expires_at'),
                user_id=page.get('user_id')
            )
            db.add(rec)

        db.commit()
        db.refresh(rec)
        return rec.to_dict()

    except Exception as e:
        db.rollback()
        print(f"❌ Error guardando página: {e}")
        raise
    finally:
        db.close()


def list_social_pages(platform: str = None) -> List[Dict]:
    """Lista páginas guardadas (opcionalmente filtradas por plataforma)."""
    db = SessionLocal()
    try:
        q = db.query(SocialPage)
        if platform:
            q = q.filter(SocialPage.platform == platform)
        return [p.to_dict() for p in q.all()]
    finally:
        db.close()

def get_social_page_by_page_id(page_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        p = db.query(SocialPage).filter(SocialPage.page_id == page_id).first()
        return p.to_dict() if p else None
    finally:
        db.close()

def get_social_page_by_instagram_id(instagram_account_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        p = db.query(SocialPage).filter(SocialPage.instagram_account_id == instagram_account_id).first()
        return p.to_dict() if p else None
    finally:
        db.close()
