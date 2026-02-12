"""
Router de Social para FastAPI
Endpoints para gestión de conexiones OAuth con redes sociales
"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.social_service import social_service
from services.publish_service import PublishService
import db_service
from database import DATABASE_URL, IS_PRODUCTION

# Instancia del servicio de publicación
publish_service = PublishService()

router = APIRouter(
    prefix="/api/social",
    tags=["Social"]
)

class TokenData(BaseModel):
    access_token: str
    refresh_token: str = None
    expires_at: str
    username: str
    user_id: str = None

@router.get("/me")
async def get_current_user(request: Request):
    """
    Obtiene información del usuario logueado
    
    Usado por: Panel web (verificar si está logueado)
    """
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user = db_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return {'success': True, 'user': user.to_dict()}

@router.get("/pages")
async def list_social_pages(platform: str | None = None, request: Request = None):
    """
    Lista páginas conectadas (Facebook/Instagram) desde la BD.
    Usado por: Panel (publish.html) para seleccionar la página/IG.
    """
    try:
        user_id = request.session.get('user_id') if request else None
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        if platform:
            pages = db_service.list_social_pages(platform=platform, user_id=user_id)
        else:
            pages = db_service.list_social_pages(user_id=user_id)
        return {"success": True, "pages": pages}
    except Exception as e:
        print(f"❌ Error en /api/social/pages: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/debug/db")
async def debug_db_config():
    """Devuelve información de la DB actual (enmascarada)."""
    try:
        url = str(DATABASE_URL)
        masked = url
        # Enmascarar credenciales si existen
        if '://' in url and '@' in url:
            scheme, rest = url.split('://', 1)
            creds, host = rest.split('@', 1)
            masked = f"{scheme}://***:***@{host}"
        return {
            'environment': 'production' if IS_PRODUCTION else 'development',
            'database_url': masked
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/logout")
async def logout(request: Request):
    """
    Cierra sesión del usuario
    
    Usado por: Panel web
    """
    request.session.clear()
    return {'success': True, 'message': 'Sesión cerrada'}

@router.get("/status")
async def get_social_status(request: Request):
    """
    Obtiene el estado de todas las conexiones sociales
    
    Usado por: Panel web (publish.html)
    """
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        social_status = social_service.get_status(user_id=user_id)
        return social_status
    except Exception as e:
        print(f"❌ Error obteniendo estado social: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/connect/{platform}")
async def connect_social_platform(platform: str, request: Request, return_url: str | None = None):
    """
    Inicia OAuth para conectar una plataforma
    
    Redirige al usuario a la página de autorización de la plataforma
    
    Usado por: Panel web (publish.html)
    """
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        # Construir redirect_uri
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/social/callback/{platform}"
        
        # Guardar return_url en sesión para volver al flujo correcto
        if return_url:
            request.session['oauth_return_url'] = return_url

        # Generar URL de autorización
        auth_data = social_service.generate_auth_url(platform, redirect_uri)
        
        # Guardar state en sesión (simplificado - en producción usar Redis/DB)
        # Por ahora lo pasamos como query param (menos seguro pero funcional)
        
        return RedirectResponse(url=auth_data['auth_url'])
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error iniciando OAuth para {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/callback/{platform}")
async def social_callback(platform: str, code: str, state: str = None, request: Request = None):
    """
    Callback OAuth para recibir tokens y loguear al usuario.
    Ahora NO llama a /me/accounts (esa lógica está centralizada en exchange_code_for_token)
    """
    try:
        # Validar sesión
        user_id = request.session.get('user_id')
        if not user_id:
            return RedirectResponse(url="/panel/login.html?error=not_authenticated")

        # Crear redirect_uri
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/social/callback/{platform}"

        # Intercambiar code -> access_token
        token_data = social_service.exchange_code_for_token(platform, code, redirect_uri, user_id)

        if not token_data:
            return RedirectResponse(url=_resolve_oauth_return_url(request, f"/panel/?error=token_exchange_failed&platform={platform}"))

        # Convertir a long-lived token (solo IG/Facebook)
        if platform in ['instagram', 'facebook']:
            print("🔄 Convirtiendo a long-lived token...")
            long_lived = social_service.exchange_for_long_lived_token(platform, token_data['access_token'])
            if long_lived:
                token_data['access_token'] = long_lived
                print("✅ Token convertido a long-lived")

        # Obtener info del usuario desde la plataforma
        user_info = social_service.get_user_info(platform, token_data['access_token'])
        if not user_info:
            return RedirectResponse(url=_resolve_oauth_return_url(request, f"/panel/?error=user_info_failed&platform={platform}"))

        # Guardar token asociado al usuario actual
        token_data['user_id'] = user_id
        token_data['username'] = user_info.get('username') or user_info.get('name')
        db_service.save_social_token(platform, token_data)

        # Actualizar metadata de usuario (opcional)
        if platform == 'instagram':
            db_service.update_user(user_id, {
                'instagram_id': user_info.get('id'),
                'instagram_username': user_info.get('username') or user_info.get('name')
            })
        elif platform == 'facebook':
            db_service.update_user(user_id, {
                'facebook_id': user_info.get('id'),
                'facebook_name': user_info.get('username') or user_info.get('name')
            })

        request.session['platform'] = platform
        request.session['username'] = user_info.get('username') or user_info.get('name')

        return RedirectResponse(url=_resolve_oauth_return_url(request, "/panel/"))

    except Exception as e:
        print(f"❌ Error en callback OAuth: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=_resolve_oauth_return_url(request, f"/panel/?error=callback_failed&platform={platform}"))

def _resolve_oauth_return_url(request: Request, fallback_url: str) -> str:
    """Devuelve la URL de retorno guardada en sesión o un fallback."""
    try:
        return_url = request.session.pop('oauth_return_url', None)
        if return_url:
            return return_url
    except Exception:
        pass
    return fallback_url

@router.post("/refresh/{platform}")
async def refresh_social_token(platform: str, request: Request):
    """
    Renueva el token de una plataforma usando refresh token
    
    Usado por: Panel web (cuando el token expira)
    """
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        token_data = social_service.refresh_token(platform, user_id=user_id)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo renovar el token de {platform}"
            )
        
        return {
            'success': True,
            'message': f'Token de {platform} renovado',
            'expires_at': token_data['expires_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error renovando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/disconnect/{platform}")
async def disconnect_social_platform(platform: str, request: Request):
    """
    Desconecta una plataforma (elimina tokens)
    
    Usado por: Panel web (publish.html)
    """
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        success = social_service.disconnect(platform, user_id=user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No se pudo desconectar {platform}"
            )
        
        return {
            'success': True,
            'message': f'{platform} desconectado exitosamente'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error desconectando: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/publish")
async def publish_to_social_networks(request: Request):
    """
    Publica un post en múltiples redes sociales
    
    Body esperado:
    {
        "codigo": "20251113-1",
        "networks": ["instagram", "linkedin", "facebook"]
    }
    
    Usado por: Panel web (publish.html)
    """
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        data = await request.json()
        codigo = data.get('codigo')
        networks = data.get('networks', [])
        
        if not codigo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de post requerido"
            )
        
        if not networks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes seleccionar al menos una red social"
            )
        
        print(f"📤 Publicando post {codigo} en: {', '.join(networks)}")
        
        # Publicar en cada red
        results = {}
        published_count = 0
        
        for network in networks:
            try:
                # Llamar al método específico de cada red
                if network == 'instagram':
                    result = publish_service.publish_to_instagram(codigo, user_id=user_id)
                elif network == 'linkedin':
                    result = publish_service.publish_to_linkedin(codigo, user_id=user_id)
                elif network == 'twitter':
                    result = publish_service.publish_to_twitter(codigo, user_id=user_id)
                elif network == 'facebook':
                    result = publish_service.publish_to_facebook(codigo, user_id=user_id)
                elif network == 'tiktok':
                    result = publish_service.publish_to_tiktok(codigo, user_id=user_id)
                else:
                    result = {'success': False, 'error': f'Red social no soportada: {network}'}
                
                results[network] = result
                
                if result.get('success'):
                    published_count += 1
                    print(f"✅ {network}: Publicado correctamente")
                else:
                    print(f"❌ {network}: {result.get('error', 'Error desconocido')}")
                    
            except Exception as e:
                print(f"❌ Error publicando en {network}: {e}")
                import traceback
                traceback.print_exc()
                results[network] = {'success': False, 'error': str(e)}
        
        # Respuesta - Permitir respuesta parcial si al menos una red tuvo éxito
        # O si todas fallaron por falta de configuración (no es un error crítico)
        all_config_errors = all(
            'no está conectado' in results[net].get('error', '').lower() or
            'no configurado' in results[net].get('error', '').lower() or
            'no disponible' in results[net].get('error', '').lower()
            for net in results
        )
        
        if published_count == 0 and not all_config_errors:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo publicar en ninguna red social"
            )
        
        # Si todas fallaron por configuración, devolver info útil
        if published_count == 0 and all_config_errors:
            return {
                'success': False,
                'published_count': 0,
                'total': len(networks),
                'results': results,
                'message': 'No se pudo publicar. Configura las credenciales de las redes sociales.',
                'config_needed': True
            }
        
        return {
            'success': True,
            'published_count': published_count,
            'total': len(networks),
            'results': results,
            'message': f'Publicado en {published_count}/{len(networks)} redes'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en publicación: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
