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

@router.get("/status")
async def get_social_status():
    """
    Obtiene el estado de todas las conexiones sociales
    
    Usado por: Panel web (social_connect.html)
    """
    try:
        status = social_service.get_status()
        return status
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
async def social_callback(platform: str, code: str, state: str, request: Request):
    """
    Callback OAuth para recibir tokens
    
    La plataforma redirige aquí después de que el usuario autoriza
    
    Usado por: OAuth flow
    """
    try:
        # Construir redirect_uri (debe ser el mismo que en connect)
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/social/callback/{platform}"
        
        # Intercambiar code por access_token
        token_data = social_service.exchange_code_for_token(platform, code, redirect_uri)
        
        if not token_data:
            return RedirectResponse(
                url=f"/panel/social_connect.html?error=token_exchange_failed&platform={platform}"
            )
        
        # Guardar token en BD
        db_service.save_social_token(platform, token_data)
        
        print(f"✅ {platform} conectado exitosamente")
        
        # Redirigir al panel con éxito
        return RedirectResponse(
            url=f"/panel/social_connect.html?success=true&platform={platform}"
        )
        
    except Exception as e:
        print(f"❌ Error en callback OAuth: {e}")
        return RedirectResponse(
            url=f"/panel/social_connect.html?error=callback_failed&platform={platform}"
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
