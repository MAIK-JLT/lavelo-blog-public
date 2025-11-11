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
import db_service

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
                token.last_used = datetime.utcnow()
            else:
                token = SocialToken(
                    user_id=user.id,
                    platform=platform,
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    expires_at=token_data.get('expires_at'),
                    username=user_info.get('username') or user_info.get('name')
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
