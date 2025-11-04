"""
Servicio de gestión de conexiones a redes sociales (OAuth)
Usado por: Panel Web, MCP Server
"""
import os
import base64
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta

class SocialService:
    """Servicio para gestionar conexiones OAuth con redes sociales"""
    
    def __init__(self):
        self.oauth_configs = {
            'instagram': {
                'client_id': os.getenv('INSTAGRAM_CLIENT_ID'),
                'client_secret': os.getenv('INSTAGRAM_CLIENT_SECRET'),
                'scope': 'instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,pages_manage_posts',
                'auth_url': 'https://www.facebook.com/v21.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v21.0/oauth/access_token',
                'user_info_url': 'https://graph.facebook.com/v21.0/me'
            },
            'linkedin': {
                'client_id': os.getenv('LINKEDIN_CLIENT_ID'),
                'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET'),
                'scope': 'w_member_social,r_basicprofile',
                'auth_url': 'https://www.linkedin.com/oauth/v2/authorization',
                'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
                'user_info_url': 'https://api.linkedin.com/v2/me'
            },
            'twitter': {
                'client_id': os.getenv('TWITTER_CLIENT_ID'),
                'client_secret': os.getenv('TWITTER_CLIENT_SECRET'),
                'scope': 'tweet.read,tweet.write,users.read',
                'auth_url': 'https://twitter.com/i/oauth2/authorize',
                'token_url': 'https://api.twitter.com/2/oauth2/token',
                'user_info_url': 'https://api.twitter.com/2/users/me'
            },
            'facebook': {
                'client_id': os.getenv('FACEBOOK_CLIENT_ID'),
                'client_secret': os.getenv('FACEBOOK_CLIENT_SECRET'),
                'scope': 'pages_manage_posts,pages_read_engagement',
                'auth_url': 'https://www.facebook.com/v18.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
                'user_info_url': 'https://graph.facebook.com/v18.0/me'
            },
            'tiktok': {
                'client_id': os.getenv('TIKTOK_CLIENT_ID'),
                'client_secret': os.getenv('TIKTOK_CLIENT_SECRET'),
                'scope': 'video.upload,user.info.basic',
                'auth_url': 'https://www.tiktok.com/auth/authorize/',
                'token_url': 'https://open-api.tiktok.com/oauth/access_token/',
                'user_info_url': 'https://open-api.tiktok.com/user/info/'
            }
        }
    
    def get_status(self) -> Dict:
        """
        Obtiene el estado de todas las conexiones sociales
        
        Returns:
            Dict con estado de cada plataforma
        """
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service
        
        tokens = db_service.get_social_tokens()
        platforms = ['instagram', 'linkedin', 'twitter', 'facebook', 'tiktok']
        status = {}
        
        for platform in platforms:
            if platform in tokens and tokens[platform]:
                token_data = tokens[platform]
                status[platform] = {
                    'connected': True,
                    'username': token_data.get('username', 'N/A'),
                    'expires_at': token_data.get('expires_at'),
                    'connected_at': token_data.get('connected_at'),
                    'last_used': token_data.get('last_used')
                }
            # Si Instagram está conectado, Facebook también lo está (mismo token)
            elif platform == 'facebook' and 'instagram' in tokens and tokens['instagram']:
                token_data = tokens['instagram']
                status[platform] = {
                    'connected': True,
                    'username': token_data.get('username', 'N/A'),
                    'expires_at': token_data.get('expires_at'),
                    'connected_at': token_data.get('connected_at'),
                    'last_used': token_data.get('last_used'),
                    'shared_with_instagram': True
                }
            else:
                status[platform] = {
                    'connected': False
                }
        
        return status
    
    def generate_auth_url(self, platform: str, redirect_uri: str) -> Dict:
        """
        Genera URL de autorización OAuth para una plataforma
        
        Args:
            platform: Plataforma (instagram, linkedin, twitter, facebook, tiktok)
            redirect_uri: URI de callback
            
        Returns:
            Dict con auth_url y state
        """
        if platform not in self.oauth_configs:
            raise ValueError(f'Plataforma no soportada: {platform}')
        
        config = self.oauth_configs[platform]
        
        if not config['client_id']:
            raise ValueError(f'Client ID no configurado para {platform}')
        
        # Generar state para seguridad
        state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
        
        # Construir URL de autorización
        auth_params = {
            'client_id': config['client_id'],
            'redirect_uri': redirect_uri,
            'scope': config['scope'],
            'response_type': 'code',
            'state': state
        }
        
        auth_url = f"{config['auth_url']}?"
        auth_url += '&'.join([f"{k}={v}" for k, v in auth_params.items()])
        
        print(f"🔗 URL OAuth generada para {platform}")
        
        return {
            'auth_url': auth_url,
            'state': state
        }
    
    def exchange_code_for_token(self, platform: str, code: str, redirect_uri: str) -> Optional[Dict]:
        """
        Intercambia authorization code por access token
        
        Args:
            platform: Plataforma
            code: Authorization code
            redirect_uri: URI de callback
            
        Returns:
            Dict con token_data o None si falla
        """
        if platform not in self.oauth_configs:
            return None
        
        config = self.oauth_configs[platform]
        
        try:
            # Preparar request
            token_params = {
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            print(f"🔄 Intercambiando code por token ({platform})")
            
            response = requests.post(config['token_url'], data=token_params)
            
            if response.status_code != 200:
                print(f"❌ Error en token exchange: {response.text}")
                return None
            
            token_data = response.json()
            
            # Obtener info del usuario
            user_info = self._get_user_info(platform, token_data['access_token'])
            
            # Calcular expiración
            expires_in = token_data.get('expires_in', 3600)
            expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': expires_at,
                'username': user_info.get('username', 'N/A'),
                'user_id': user_info.get('id'),
                'connected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error intercambiando token: {e}")
            return None
    
    def _get_user_info(self, platform: str, access_token: str) -> Dict:
        """
        Obtiene información del usuario desde la API
        
        Args:
            platform: Plataforma
            access_token: Token de acceso
            
        Returns:
            Dict con info del usuario
        """
        if platform not in self.oauth_configs:
            return {}
        
        config = self.oauth_configs[platform]
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(config['user_info_url'], headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Normalizar respuesta según plataforma
                if platform == 'instagram' or platform == 'facebook':
                    return {
                        'id': user_data.get('id'),
                        'username': user_data.get('name', user_data.get('username', 'N/A'))
                    }
                elif platform == 'linkedin':
                    return {
                        'id': user_data.get('id'),
                        'username': f"{user_data.get('localizedFirstName', '')} {user_data.get('localizedLastName', '')}"
                    }
                elif platform == 'twitter':
                    return {
                        'id': user_data.get('data', {}).get('id'),
                        'username': user_data.get('data', {}).get('username', 'N/A')
                    }
                elif platform == 'tiktok':
                    return {
                        'id': user_data.get('data', {}).get('user', {}).get('open_id'),
                        'username': user_data.get('data', {}).get('user', {}).get('display_name', 'N/A')
                    }
            
            return {}
            
        except Exception as e:
            print(f"❌ Error obteniendo info de usuario: {e}")
            return {}
    
    def refresh_token(self, platform: str) -> Optional[Dict]:
        """
        Renueva el access token usando refresh token
        
        Args:
            platform: Plataforma
            
        Returns:
            Dict con nuevo token_data o None si falla
        """
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service
        
        tokens = db_service.get_social_tokens()
        
        if platform not in tokens or not tokens[platform]:
            return None
        
        token_data = tokens[platform]
        refresh_token = token_data.get('refresh_token')
        
        if not refresh_token:
            return None
        
        config = self.oauth_configs[platform]
        
        try:
            refresh_params = {
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            print(f"🔄 Renovando token ({platform})")
            
            response = requests.post(config['token_url'], data=refresh_params)
            
            if response.status_code != 200:
                print(f"❌ Error renovando token: {response.text}")
                return None
            
            new_token_data = response.json()
            
            # Actualizar token_data
            expires_in = new_token_data.get('expires_in', 3600)
            expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            updated_data = {
                'access_token': new_token_data['access_token'],
                'refresh_token': new_token_data.get('refresh_token', refresh_token),
                'expires_at': expires_at,
                'username': token_data.get('username'),
                'user_id': token_data.get('user_id'),
                'connected_at': token_data.get('connected_at')
            }
            
            # Guardar en BD
            db_service.save_social_token(platform, updated_data)
            
            return updated_data
            
        except Exception as e:
            print(f"❌ Error renovando token: {e}")
            return None
    
    def disconnect(self, platform: str) -> bool:
        """
        Desconecta una plataforma (elimina tokens)
        
        Args:
            platform: Plataforma
            
        Returns:
            True si se desconectó correctamente
        """
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service
        
        try:
            db_service.delete_social_token(platform)
            print(f"✅ {platform} desconectado")
            return True
        except Exception as e:
            print(f"❌ Error desconectando {platform}: {e}")
            return False

# Instancia global
social_service = SocialService()
