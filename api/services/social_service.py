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
        pass

    @property
    def oauth_configs(self):
        """Lee las credenciales del entorno en cada acceso (lazy load)."""
        return {
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

    def get_status(self, user_id: Optional[int] = None) -> Dict:
        """
        Obtiene el estado de todas las conexiones sociales

        Returns:
            Dict con estado de cada plataforma
        """
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service

        tokens = db_service.get_social_tokens(user_id=user_id)
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

        state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')

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

    def exchange_code_for_token(self, platform: str, code: str, redirect_uri: str, current_user_id: int) -> Optional[Dict]:
        """Intercambia code por token, guardando páginas si aplica."""
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service

        try:
            if platform in ['instagram', 'facebook']:
                fb_client_id = os.getenv('FACEBOOK_CLIENT_ID')
                fb_client_secret = os.getenv('FACEBOOK_CLIENT_SECRET')

                # 1) CODE -> SHORT TOKEN
                short_resp = requests.get(
                    "https://graph.facebook.com/v21.0/oauth/access_token",
                    params={
                        "client_id": fb_client_id,
                        "redirect_uri": redirect_uri,
                        "client_secret": fb_client_secret,
                        "code": code
                    }
                )
                if short_resp.status_code != 200:
                    print("❌ Error short token:", short_resp.text)
                    return None

                short_token = short_resp.json().get("access_token")

                # 2) SHORT -> LONG TOKEN
                long_resp = requests.get(
                    "https://graph.facebook.com/v21.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": fb_client_id,
                        "client_secret": fb_client_secret,
                        "fb_exchange_token": short_token
                    }
                )

                if long_resp.status_code != 200:
                    print("❌ Error long token:", long_resp.text)
                    return None

                long_json = long_resp.json()
                user_long_token = long_json.get("access_token")

                # 3) Obtener páginas del usuario
                pages_resp = requests.get(
                    "https://graph.facebook.com/v21.0/me/accounts",
                    params={
                        "access_token": user_long_token,
                        "fields": "id,name,access_token,instagram_business_account"
                    }
                )
                print("📄 /me/accounts =>", pages_resp.text)

                if pages_resp.status_code != 200:
                    print("❌ Error /me/accounts:", pages_resp.text)
                    return None

                pages_json = pages_resp.json().get("data", [])

                pages_all = []
                pages_with_ig = []

                for p in pages_json:
                    pid = p.get("id")
                    pname = p.get("name")
                    page_token = p.get("access_token")
                    ig_acc = p.get("instagram_business_account", {})
                    ig_id_local = ig_acc.get("id")

                    db_service.upsert_social_page({
                        'user_id': current_user_id,
                        'platform': 'facebook_page',
                        'page_id': pid,
                        'page_name': pname,
                        'instagram_account_id': ig_id_local,
                        'page_access_token': page_token,
                        'expires_at': None
                    })

                    row = {
                        'id': pid,
                        'name': pname,
                        'access_token': page_token,
                        'instagram_id': ig_id_local
                    }
                    pages_all.append(row)
                    if ig_id_local:
                        pages_with_ig.append(row)

                if not pages_all:
                    print("⚠️ Usuario sin páginas")
                    return None

                selected = pages_with_ig[0] if pages_with_ig else pages_all[0]

                me_resp = requests.get(
                    "https://graph.facebook.com/v21.0/me",
                    params={"fields": "id,name", "access_token": user_long_token}
                )
                if me_resp.status_code == 200:
                    me_json = me_resp.json()
                    user_meta_id = me_json.get("id")
                    username = me_json.get("name")
                else:
                    user_meta_id = None
                    username = "N/A"

                return {
                    "access_token": user_long_token,
                    "refresh_token": None,
                    "expires_in": long_json.get("expires_in", 5184000),
                    "username": username,
                    "user_id": user_meta_id,
                    "pages": pages_all,
                    "page_id": selected["id"],
                    "instagram_account_id": selected["instagram_id"],
                    "user_long_lived_token": user_long_token
                }

            # Fallback genérico para otras plataformas
            if platform not in self.oauth_configs:
                return None

            config = self.oauth_configs[platform]
            token_data = requests.post(
                config['token_url'],
                data={
                    'client_id': config['client_id'],
                    'client_secret': config['client_secret'],
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }
            )

            if token_data.status_code != 200:
                print(f"❌ Error token {platform}: {token_data.text}")
                return None

            data = token_data.json()
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in', 3600),
                'username': None,
                'user_id': None
            }

        except Exception as e:
            print("❌ ERROR TOKEN EXCHANGE:", e)
            import traceback
            traceback.print_exc()
            return None

    def get_user_info(self, platform: str, access_token: str) -> Dict:
        """
        Obtiene información del usuario desde la API (público)
        """
        return self._get_user_info(platform, access_token)

    def _get_user_info(self, platform: str, access_token: str) -> Dict:
        if platform not in self.oauth_configs:
            return {}

        config = self.oauth_configs[platform]

        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(config['user_info_url'], headers=headers)

            if response.status_code == 200:
                user_data = response.json()

                if platform in ['instagram', 'facebook']:
                    return {
                        'id': user_data.get('id'),
                        'username': user_data.get('name', user_data.get('username', 'N/A'))
                    }
                if platform == 'linkedin':
                    return {
                        'id': user_data.get('id'),
                        'username': f"{user_data.get('localizedFirstName', '')} {user_data.get('localizedLastName', '')}".strip()
                    }
                if platform == 'twitter':
                    return {
                        'id': user_data.get('data', {}).get('id'),
                        'username': user_data.get('data', {}).get('username', 'N/A')
                    }
                if platform == 'tiktok':
                    return {
                        'id': user_data.get('data', {}).get('user', {}).get('open_id'),
                        'username': user_data.get('data', {}).get('user', {}).get('display_name', 'N/A')
                    }

            return {}

        except Exception as e:
            print(f"❌ Error obteniendo info de usuario: {e}")
            return {}

    def refresh_token(self, platform: str, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        Renueva el access token usando refresh token
        """
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service

        tokens = db_service.get_social_tokens(user_id=user_id)

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

            db_service.save_social_token(platform, updated_data)

            return updated_data

        except Exception as e:
            print(f"❌ Error renovando token: {e}")
            return None

    def exchange_for_long_lived_token(self, platform: str, short_lived_token: str) -> Optional[str]:
        """
        Intercambia un short-lived token por uno long-lived (60 días)
        Solo para Facebook/Instagram
        """
        if platform not in ['instagram', 'facebook']:
            return None

        config = self.oauth_configs[platform]

        try:
            exchange_url = 'https://graph.facebook.com/v21.0/oauth/access_token'
            params = {
                'grant_type': 'fb_exchange_token',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'fb_exchange_token': short_lived_token
            }

            response = requests.get(exchange_url, params=params)

            if response.status_code != 200:
                print(f"❌ Error intercambiando por long-lived token: {response.text}")
                return None

            data = response.json()
            return data.get('access_token')

        except Exception as e:
            print(f"❌ Error en exchange_for_long_lived_token: {e}")
            return None

    def disconnect(self, platform: str, user_id: Optional[int] = None) -> bool:
        """
        Desconecta una plataforma (elimina tokens)
        """
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service

        try:
            db_service.delete_social_token(platform, user_id=user_id)
            print(f"✅ {platform} desconectado")
            return True
        except Exception as e:
            print(f"❌ Error desconectando {platform}: {e}")
            return False


# Instancia global
social_service = SocialService()
