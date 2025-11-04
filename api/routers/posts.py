"""
Router de Posts para FastAPI
Endpoints HTTP para el panel web
"""
from fastapi import APIRouter, HTTPException, status, Request
from typing import List, Optional
import sys
import os

# Agregar path para importar modelos y servicios
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.post import Post, PostCreate, PostUpdate
from services.post_service import PostService

router = APIRouter(
    prefix="/api/posts",
    tags=["Posts"]
)

# Instancia del servicio
post_service = PostService()

@router.get("/", response_model=dict)
async def list_posts(limit: Optional[int] = None):
    """
    Lista todos los posts
    
    Usado por: Panel web (selector de posts)
    """
    try:
        posts = await post_service.list_posts(limit=limit)
        return {
            'success': True,
            'posts': posts
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{codigo}", response_model=dict)
async def get_post(codigo: str):
    """
    Obtiene un post por código
    
    Usado por: Panel web (cargar detalles)
    """
    try:
        post = await post_service.get_post(codigo)
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post {codigo} no encontrado"
            )
        
        return {
            'success': True,
            'post': post
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/", response_model=dict)
async def create_post(post: PostCreate):
    """
    Crea un nuevo post
    
    Usado por: Panel web (botón crear), MCP
    """
    try:
        result = await post_service.create_post(
            titulo=post.titulo,
            categoria=post.categoria,
            idea=post.idea,
            fecha_programada=str(post.fecha_programada) if post.fecha_programada else None,
            hora_programada=post.hora_programada
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/{codigo}", response_model=dict)
async def update_post(codigo: str, updates: PostUpdate):
    """
    Actualiza un post
    
    Usado por: Panel web (guardar cambios)
    """
    try:
        # Convertir a dict y eliminar None
        updates_dict = updates.model_dump(exclude_unset=True)
        
        result = await post_service.update_post(codigo, updates_dict)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{codigo}", response_model=dict)
async def delete_post(codigo: str):
    """
    Elimina un post
    
    Usado por: Panel web (botón eliminar)
    """
    try:
        result = await post_service.delete_post(codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{codigo}/init-folders", response_model=dict)
async def init_post_folders(codigo: str):
    """
    Inicializa carpetas de Drive para un post
    
    Usado por: Panel web, MCP
    """
    try:
        result = await post_service.init_post_folders(codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{codigo}/update-networks", response_model=dict)
async def update_networks(codigo: str, networks: dict):
    """
    Actualiza la selección de redes sociales para un post
    
    Usado por: Panel web (checkboxes de redes)
    """
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service
        
        # Actualizar cada red en la BD
        updates = {}
        for network, active in networks.items():
            field_name = f'redes_{network}'
            updates[field_name] = active
        
        success = db_service.update_post(codigo, updates)
        
        if not success:
            raise Exception(f"Error actualizando redes para {codigo}")
        
        return {
            'success': True,
            'message': 'Redes actualizadas correctamente'
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{codigo}/reset-phases", response_model=dict)
async def reset_phases(codigo: str, data: dict):
    """
    Resetea fases dependientes cuando se edita contenido validado
    
    Usado por: Panel web (al guardar cambios en fases validadas)
    """
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import db_service
        
        estado = data.get('estado')
        
        # Mapeo de estados a checkboxes que deben resetearse
        reset_map = {
            'BASE_TEXT_AWAITING': ['adapted_texts', 'image_prompt', 'image_base', 'image_formats', 
                                   'video_script', 'video_base', 'video_formats'],
            'ADAPTED_TEXTS_AWAITING': ['image_prompt', 'image_base', 'image_formats', 
                                       'video_script', 'video_base', 'video_formats'],
            'IMAGE_PROMPT_AWAITING': ['image_base', 'image_formats', 'video_script', 
                                      'video_base', 'video_formats'],
            'VIDEO_PROMPT_AWAITING': ['video_base', 'video_formats']
        }
        
        checkboxes_to_reset = reset_map.get(estado, [])
        
        # Resetear checkboxes
        updates = {'estado': estado}
        for checkbox in checkboxes_to_reset:
            updates[checkbox] = False
        
        success = db_service.update_post(codigo, updates)
        
        if not success:
            raise Exception(f"Error reseteando fases para {codigo}")
        
        return {
            'success': True,
            'message': 'Fases reseteadas correctamente',
            'reset_checkboxes': checkboxes_to_reset
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{codigo}/upload-image", response_model=dict)
async def upload_image(codigo: str, request: Request):
    """
    Sube una imagen manualmente para reemplazar la generada
    
    Usado por: Panel web (Fase 4 - reemplazar imagen)
    """
    try:
        import sys
        import os
        import base64
        import json
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from services.file_service import FileService
        import db_service
        
        file_service = FileService()
        
        # Leer body como texto (no como dict para evitar validación)
        body_bytes = await request.body()
        body_text = body_bytes.decode('utf-8')
        data = json.loads(body_text)
        
        # Decodificar imagen base64
        image_data = data.get('image_data', '')
        filename = data.get('filename', f'{codigo}_imagen_base.png')
        
        if not image_data:
            raise Exception("No se proporcionó imagen")
        
        # Remover prefijo data:image/...;base64, si existe
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decodificar y guardar
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as decode_error:
            raise Exception(f"Error decodificando base64: {decode_error}")
        
        # Guardar archivo binario usando el método privado
        file_path = file_service._get_file_path(codigo, 'imagenes', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        
        print(f"💾 Imagen guardada: {file_path} ({len(image_bytes) / 1024:.2f} KB)")
        
        # Actualizar checkbox en BD
        db_service.update_post(codigo, {'imagen_base_png': True})
        
        return {
            'success': True,
            'message': f'Imagen {filename} subida correctamente',
            'filename': filename
        }
    except Exception as e:
        print(f"❌ Error subiendo imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
