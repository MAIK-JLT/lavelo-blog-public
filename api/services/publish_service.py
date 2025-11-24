"""
Servicio de publicación en redes sociales
Usado por: Panel Web, MCP Server
"""
import os
import sys
import requests
from typing import Dict, Optional
from dotenv import load_dotenv

# Cargar variables de entorno (producción primero, luego fallback local)
default_env = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service
from services.file_service import file_service
from services.limits_service import limits_service

class PublishService:
    """Servicio para publicar contenido en redes sociales"""
    
    def publish_to_instagram(self, codigo: str, caption: str = None, user_id: int = None,
                              page_id: str = None, instagram_account_id: str = None) -> Dict:
        """
        Publica en Instagram
        
        Args:
            codigo: Código del post
            user_id: ID del usuario (para verificar límites)
            caption: Texto del post (opcional, usa instagram.txt si no se proporciona)
            
        Returns:
            Dict con success y post_id o error
        """
        try:
            # Verificar límite de publicación
            if user_id:
                limit_check = limits_service.check_publish_limit(user_id)
                if not limit_check['allowed']:
                    return {
                        'success': False,
                        'error': limit_check['message'],
                        'upgrade_required': limit_check.get('upgrade_required', False)
                    }
            
            # Obtener token e IDs
            access_token = None
            # Si el usuario especifica una página/IG, usar SocialPage
            if page_id or instagram_account_id:
                page_rec = None
                if page_id:
                    page_rec = db_service.get_social_page_by_page_id(page_id)
                if not page_rec and instagram_account_id:
                    page_rec = db_service.get_social_page_by_instagram_id(instagram_account_id)
                if not page_rec:
                    return {'success': False, 'error': 'Página/IG seleccionada no encontrada. Reconecta Instagram.'}
                access_token = page_rec.get('page_access_token')
                instagram_account_id = page_rec.get('instagram_account_id')
            else:
                return {
                    'success': False,
                    'error': 'Debes seleccionar una página con Instagram asociado. No se puede usar un token global.'
                }

            print(f"🔑 Token: {access_token[:50]}...")
            print(f"📱 Instagram Account ID: {instagram_account_id}")
            
            if not instagram_account_id:
                return {'success': False, 'error': 'Instagram Business Account ID no disponible. Reconecta Instagram.'}
            
            # Obtener caption si no se proporciona
            if not caption:
                # Leer desde storage local
                storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'storage', 'posts', codigo, 'textos', f'{codigo}_instagram.txt')
                if os.path.exists(storage_path):
                    with open(storage_path, 'r', encoding='utf-8') as f:
                        caption = f.read()
                else:
                    return {'success': False, 'error': f'No se encontró texto de Instagram en {storage_path}'}
            
            # Obtener URL de imagen (debe ser pública)
            # TODO: Subir imagen a servidor público o usar Cloudinary
            image_url = f"https://blog.lavelo.es/storage/posts/{codigo}/imagenes/{codigo}_instagram_1x1.png"
            
            # Paso 1: Crear media container
            create_url = f'https://graph.facebook.com/v18.0/{instagram_account_id}/media'
            create_data = {
                'image_url': image_url,
                'caption': caption,
                'access_token': access_token
            }
            
            print(f"📸 Creando container en Instagram...")
            response = requests.post(create_url, data=create_data)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'Error creando container: {response.text}'}
            
            container_id = response.json()['id']
            
            # Paso 2: Publicar
            publish_url = f'https://graph.facebook.com/v18.0/{instagram_account_id}/media_publish'
            publish_data = {
                'creation_id': container_id,
                'access_token': access_token
            }
            
            print(f"✅ Publicando en Instagram...")
            response = requests.post(publish_url, data=publish_data)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'Error publicando: {response.text}'}
            
            post_id = response.json()['id']
            print(f"🎉 Publicado en Instagram: {post_id}")
            
            # Incrementar contador de publicaciones
            if user_id:
                limits_service.increment_publish_count(user_id)
            
            return {
                'success': True,
                'post_id': post_id,
                'platform': 'instagram'
            }
            
        except Exception as e:
            print(f"❌ Error publicando en Instagram: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_facebook(self, codigo: str, message: str = None,
                            page_id: str = None) -> Dict:
        """
        Publica en Facebook
        
        Args:
            codigo: Código del post
            message: Texto del post (opcional, usa facebook.txt si no se proporciona)
            
        Returns:
            Dict con success y post_id o error
        """
        try:
            # Obtener token de página
            access_token = None
            if page_id:
                page_rec = db_service.get_social_page_by_page_id(page_id)
                if not page_rec:
                    return {'success': False, 'error': 'Página seleccionada no encontrada. Reconecta Facebook/Instagram.'}
                access_token = page_rec.get('page_access_token')
            else:
                # Fallback a token global previo (si existiese)
                tokens = db_service.get_social_tokens()
                if 'instagram' not in tokens or not tokens['instagram']:
                    return {'success': False, 'error': 'Facebook/Instagram no está conectado'}
                token_data = tokens['instagram']
                access_token = token_data['access_token']
                page_id = token_data.get('page_id')
            
            if not page_id:
                return {'success': False, 'error': 'Facebook Page ID no disponible. Reconecta Facebook/Instagram.'}
            
            # Obtener mensaje si no se proporciona
            if not message:
                # Leer desde storage local
                storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'storage', 'posts', codigo, 'textos', f'{codigo}_facebook.txt')
                if os.path.exists(storage_path):
                    with open(storage_path, 'r', encoding='utf-8') as f:
                        message = f.read()
                else:
                    return {'success': False, 'error': f'No se encontró texto de Facebook en {storage_path}'}
            
            # Obtener URL de imagen
            image_url = f"https://blog.lavelo.es/storage/posts/{codigo}/imagenes/{codigo}_facebook_16x9.png"
            
            url = f'https://graph.facebook.com/v18.0/{page_id}/photos'
            
            data = {
                'url': image_url,
                'caption': message,
                'access_token': access_token
            }
            
            print(f"📘 Publicando en Facebook...")
            response = requests.post(url, data=data)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'Error publicando: {response.text}'}
            
            post_id = response.json()['id']
            print(f"🎉 Publicado en Facebook: {post_id}")
            
            return {
                'success': True,
                'post_id': post_id,
                'platform': 'facebook'
            }
            
        except Exception as e:
            print(f"❌ Error publicando en Facebook: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_linkedin(self, codigo: str, text: str = None) -> Dict:
        """
        Publica en LinkedIn
        
        Args:
            codigo: Código del post
            text: Texto del post (opcional, usa linkedin.txt si no se proporciona)
            
        Returns:
            Dict con success y post_id o error
        """
        try:
            # Obtener token
            tokens = db_service.get_social_tokens()
            if 'linkedin' not in tokens or not tokens['linkedin']:
                return {'success': False, 'error': 'LinkedIn no está conectado'}
            
            token_data = tokens['linkedin']
            access_token = token_data['access_token']
            
            # Obtener texto si no se proporciona
            if not text:
                # Leer desde storage local
                storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'storage', 'posts', codigo, 'textos', f'{codigo}_linkedin.txt')
                if os.path.exists(storage_path):
                    with open(storage_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                else:
                    return {'success': False, 'error': f'No se encontró texto de LinkedIn en {storage_path}'}
            
            # LinkedIn API v2
            url = 'https://api.linkedin.com/v2/ugcPosts'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # TODO: Obtener person_id del token
            # Por ahora solo publicamos texto
            
            data = {
                'author': f"urn:li:person:{token_data.get('user_id', 'PERSON_ID')}",
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {
                            'text': text
                        },
                        'shareMediaCategory': 'NONE'
                    }
                },
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
                }
            }
            
            print(f"💼 Publicando en LinkedIn...")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 201:
                return {'success': False, 'error': f'Error publicando: {response.text}'}
            
            post_id = response.json()['id']
            print(f"🎉 Publicado en LinkedIn: {post_id}")
            
            return {
                'success': True,
                'post_id': post_id,
                'platform': 'linkedin'
            }
            
        except Exception as e:
            print(f"❌ Error publicando en LinkedIn: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_twitter(self, codigo: str, text: str = None) -> Dict:
        """
        Publica en Twitter
        
        Args:
            codigo: Código del post
            text: Texto del post (opcional, usa twitter.txt si no se proporciona)
            
        Returns:
            Dict con success y tweet_id o error
        """
        try:
            # Obtener token
            tokens = db_service.get_social_tokens()
            if 'twitter' not in tokens or not tokens['twitter']:
                return {'success': False, 'error': 'Twitter no está conectado'}
            
            token_data = tokens['twitter']
            access_token = token_data['access_token']
            
            # Obtener texto si no se proporciona
            if not text:
                # Leer desde storage local
                storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'storage', 'posts', codigo, 'textos', f'{codigo}_twitter.txt')
                if os.path.exists(storage_path):
                    with open(storage_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                else:
                    return {'success': False, 'error': f'No se encontró texto de Twitter en {storage_path}'}
            
            # Twitter API v2
            url = 'https://api.twitter.com/2/tweets'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # TODO: Implementar subida de media
            # Por ahora solo texto
            
            data = {
                'text': text
            }
            
            print(f"🐦 Publicando en Twitter...")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 201:
                return {'success': False, 'error': f'Error publicando: {response.text}'}
            
            tweet_id = response.json()['data']['id']
            print(f"🎉 Publicado en Twitter: {tweet_id}")
            
            return {
                'success': True,
                'tweet_id': tweet_id,
                'platform': 'twitter'
            }
            
        except Exception as e:
            print(f"❌ Error publicando en Twitter: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_tiktok(self, codigo: str, description: str = None) -> Dict:
        """
        Publica en TikTok
        
        Args:
            codigo: Código del post
            description: Descripción del video (opcional, usa tiktok.txt si no se proporciona)
            
        Returns:
            Dict con success y video_id o error
        """
        try:
            # Obtener token
            tokens = db_service.get_social_tokens()
            if 'tiktok' not in tokens or not tokens['tiktok']:
                return {'success': False, 'error': 'TikTok no está conectado'}
            
            # TODO: Implementar subida de video a TikTok
            # TikTok API requiere proceso más complejo
            
            return {
                'success': False,
                'error': 'Publicación en TikTok aún no implementada'
            }
            
        except Exception as e:
            print(f"❌ Error publicando en TikTok: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_all(self, codigo: str, platforms: list = None,
                       page_id: str = None, instagram_account_id: str = None) -> Dict:
        """
        Publica en múltiples plataformas
        
        Args:
            codigo: Código del post
            platforms: Lista de plataformas (opcional, usa todas las conectadas)
            
        Returns:
            Dict con resultados por plataforma
        """
        if not platforms:
            # Obtener plataformas conectadas
            tokens = db_service.get_social_tokens()
            platforms = [p for p in tokens.keys() if tokens[p]]
        
        results = {}
        
        for platform in platforms:
            if platform == 'instagram':
                results['instagram'] = self.publish_to_instagram(codigo,
                                                                 page_id=page_id,
                                                                 instagram_account_id=instagram_account_id)
            elif platform == 'facebook':
                results['facebook'] = self.publish_to_facebook(codigo,
                                                               page_id=page_id)
            elif platform == 'linkedin':
                results['linkedin'] = self.publish_to_linkedin(codigo)
            elif platform == 'twitter':
                results['twitter'] = self.publish_to_twitter(codigo)
            elif platform == 'tiktok':
                results['tiktok'] = self.publish_to_tiktok(codigo)
        
        # Contar éxitos
        successful = sum(1 for r in results.values() if r.get('success'))
        total = len(results)
        
        return {
            'success': successful > 0,
            'published': successful,
            'total': total,
            'results': results
        }

# Instancia global
publish_service = PublishService()
