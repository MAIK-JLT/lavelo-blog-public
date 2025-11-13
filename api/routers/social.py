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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado"
        )
    
    return {
        'user_id': user_id,
        'platform': request.session.get('platform'),
        'username': request.session.get('username')
    }

@router.post("/logout")
async def logout(request: Request):
    """
    Cierra sesión del usuario
    
    Usado por: Panel web
    """
    request.session.clear()
    return {'success': True, 'message': 'Sesión cerrada'}

@router.get("/status")
async def get_social_status():
    """
    Obtiene el estado de todas las conexiones sociales
    
    Usado por: Panel web (social_connect.html)
    """
    try:
        social_status = social_service.get_status()
        return social_status
    except Exception as e:
        print(f"❌ Error obteniendo estado social: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/connect/{platform}")
async def connect_social_platform(platform: str, request: Request):
    """
    Inicia OAuth para conectar una plataforma
    
    Redirige al usuario a la página de autorización de la plataforma
    
    Usado por: Panel web (social_connect.html)
    """
    try:
        # Construir redirect_uri
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/social/callback/{platform}"
        
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
    Callback OAuth para recibir tokens
    
    La plataforma redirige aquí después de que el usuario autoriza
    Este callback también LOGUEA al usuario (crea sesión)
    
    Usado por: OAuth flow + Login
    """
    try:
        # Construir redirect_uri (debe ser el mismo que en connect)
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/social/callback/{platform}"
        
        # Intercambiar code por access_token
        token_data = social_service.exchange_code_for_token(platform, code, redirect_uri)
        
        if not token_data:
            return RedirectResponse(
                url=f"/panel/?error=token_exchange_failed&platform={platform}"
            )
        
        # Obtener info del usuario de la plataforma
        user_info = social_service.get_user_info(platform, token_data['access_token'])
        
        if not user_info:
            return RedirectResponse(
                url=f"/panel/?error=user_info_failed&platform={platform}"
            )
        
        # Crear o actualizar usuario en BD
        from database import SessionLocal
        from db_models import User, SocialToken
        from datetime import datetime
        
        db = SessionLocal()
        try:
            # Buscar usuario existente por platform_id
            if platform == 'instagram':
                user = db.query(User).filter(User.instagram_id == user_info['id']).first()
                if not user:
                    user = User(
                        instagram_id=user_info['id'],
                        instagram_username=user_info.get('username')
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                else:
                    user.instagram_username = user_info.get('username')
                    user.last_login = datetime.utcnow()
                    db.commit()
            
            elif platform == 'facebook':
                user = db.query(User).filter(User.facebook_id == user_info['id']).first()
                if not user:
                    user = User(
                        facebook_id=user_info['id'],
                        facebook_name=user_info.get('name')
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                else:
                    user.facebook_name = user_info.get('name')
                    user.last_login = datetime.utcnow()
                    db.commit()
            
            # Obtener page_id e instagram_account_id para Instagram/Facebook
            page_id = None
            instagram_account_id = None
            
            print(f"🔍 Platform: {platform}, obteniendo IDs...")
            
            if platform == 'instagram' or platform == 'facebook':
                # Obtener páginas de Facebook del usuario
                import requests
                print(f"📡 Consultando páginas de Facebook...")
                pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={token_data['access_token']}"
                pages_response = requests.get(pages_url)
                print(f"📊 Response status: {pages_response.status_code}")
                
                if pages_response.status_code == 200:
                    pages_data = pages_response.json()
                    print(f"📋 Pages data: {pages_data}")
                    
                    # Si no hay páginas (permisos no aprobados), usar fallback del .env
                    if not pages_data.get('data') or len(pages_data['data']) == 0:
                        print("⚠️  No se encontraron páginas. Usando IDs del .env como fallback...")
                        page_id = os.getenv('FACEBOOK_PAGE_ID')
                        instagram_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
                        if page_id:
                            print(f"✅ Usando FACEBOOK_PAGE_ID del .env: {page_id}")
                        if instagram_account_id:
                            print(f"✅ Usando INSTAGRAM_BUSINESS_ACCOUNT_ID del .env: {instagram_account_id}")
                    elif pages_data.get('data') and len(pages_data['data']) > 0:
                        # Tomar la primera página
                        page_id = pages_data['data'][0]['id']
                        
                        # Obtener Instagram Business Account ID de la página
                        ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={token_data['access_token']}"
                        ig_response = requests.get(ig_url)
                        
                        if ig_response.status_code == 200:
                            ig_data = ig_response.json()
                            instagram_account_id = ig_data.get('instagram_business_account', {}).get('id')
                            print(f"✅ Instagram Business Account ID: {instagram_account_id}")
                        
                        print(f"✅ Facebook Page ID: {page_id}")
            
            # Guardar/actualizar token
            token = db.query(SocialToken).filter(
                SocialToken.user_id == user.id,
                SocialToken.platform == platform
            ).first()
            
            if token:
                token.access_token = token_data['access_token']
                token.refresh_token = token_data.get('refresh_token')
                token.expires_at = token_data.get('expires_at')
                token.username = user_info.get('username') or user_info.get('name')
                token.page_id = page_id
                token.instagram_account_id = instagram_account_id
                token.last_used = datetime.utcnow()
            else:
                token = SocialToken(
                    user_id=user.id,
                    platform=platform,
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    expires_at=token_data.get('expires_at'),
                    username=user_info.get('username') or user_info.get('name'),
                    page_id=page_id,
                    instagram_account_id=instagram_account_id
                )
                db.add(token)
            
            db.commit()
            
            # Crear sesión (LOGIN)
            request.session['user_id'] = user.id
            request.session['platform'] = platform
            request.session['username'] = user_info.get('username') or user_info.get('name')
            
            print(f"✅ Usuario {user.id} logueado con {platform}")
            
            # Redirigir al panel (ya logueado)
            return RedirectResponse(url="/panel/")
            
        finally:
            db.close()
        
    except Exception as e:
        print(f"❌ Error en callback OAuth: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f"/panel/?error=callback_failed&platform={platform}"
        )

@router.post("/refresh/{platform}")
async def refresh_social_token(platform: str):
    """
    Renueva el token de una plataforma usando refresh token
    
    Usado por: Panel web (cuando el token expira)
    """
    try:
        token_data = social_service.refresh_token(platform)
        
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
async def disconnect_social_platform(platform: str):
    """
    Desconecta una plataforma (elimina tokens)
    
    Usado por: Panel web (social_connect.html)
    """
    try:
        success = social_service.disconnect(platform)
        
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
                    result = publish_service.publish_to_instagram(codigo)
                elif network == 'linkedin':
                    result = publish_service.publish_to_linkedin(codigo)
                elif network == 'twitter':
                    result = publish_service.publish_to_twitter(codigo)
                elif network == 'facebook':
                    result = publish_service.publish_to_facebook(codigo)
                elif network == 'tiktok':
                    result = publish_service.publish_to_tiktok(codigo)
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
