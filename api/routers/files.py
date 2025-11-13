"""
Router de Files para FastAPI
Endpoints para leer/escribir archivos (reemplaza Drive)
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import Response, FileResponse
from typing import Optional
import sys
import os

# Agregar path para importar servicios
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.file_service import file_service

router = APIRouter(
    prefix="/api/files",
    tags=["Files"]
)

@router.get("/{codigo}/{folder}/{filename}")
async def get_file(codigo: str, folder: str, filename: str):
    """
    Obtiene un archivo (texto o binario)
    
    Usado por: Panel web (cargar textos, imágenes)
    """
    try:
        # Detectar si es texto o binario por extensión
        is_text = filename.endswith(('.txt', '.md', '.json', '.html', '.css', '.js'))
        
        if is_text:
            content = file_service.read_file(codigo, folder, filename)
            if content is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Archivo {filename} no encontrado"
                )
            return {'success': True, 'content': content}
        else:
            # Archivo binario (imagen, video)
            data = file_service.read_binary_file(codigo, folder, filename)
            if data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Archivo {filename} no encontrado"
                )
            
            # Detectar content type
            content_type = 'application/octet-stream'
            if filename.endswith('.png'):
                content_type = 'image/png'
            elif filename.endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif filename.endswith('.mp4'):
                content_type = 'video/mp4'
            
            return Response(content=data, media_type=content_type)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{codigo}/{folder}/{filename}")
async def save_file(codigo: str, folder: str, filename: str, content: dict):
    """
    Guarda un archivo de texto
    
    Body: {"content": "texto del archivo"}
    
    Usado por: Panel web (guardar textos editados)
    """
    try:
        text_content = content.get('content', '')
        
        success = file_service.save_file(codigo, folder, filename, text_content)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando archivo"
            )
        
        # Si es prompt de imagen, resetear fases dependientes
        if 'prompt_imagen' in filename:
            print(f"🔄 Prompt de imagen modificado, reseteando fases dependientes...")
            post = db_service.get_post_by_codigo(codigo)
            
            if post and post.get('estado') not in ['DRAFT', 'BASE_TEXT_AWAITING', 'ADAPTED_TEXTS_AWAITING', 'IMAGE_PROMPT_AWAITING']:
                # Resetear checkboxes de imagen
                db_service.update_post(codigo, {
                    'imagen_base_png': False,
                    'instagram_1x1_png': False,
                    'instagram_stories_9x16_png': False,
                    'linkedin_16x9_png': False,
                    'twitter_16x9_png': False,
                    'facebook_16x9_png': False,
                    'estado': 'IMAGE_PROMPT_AWAITING'
                })
                print(f"✅ Fases de imagen reseteadas, estado → IMAGE_PROMPT_AWAITING")
        
        return {
            'success': True,
            'message': f"✅ Archivo {filename} guardado"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{codigo}/{folder}/upload")
async def upload_file(codigo: str, folder: str, file: UploadFile = File(...)):
    """
    Sube un archivo binario (imagen, video)
    
    Usado por: Panel web (subir imágenes manualmente)
    """
    try:
        # Leer contenido del archivo
        data = await file.read()
        
        # Guardar
        success = file_service.save_binary_file(codigo, folder, file.filename, data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando archivo"
            )
        
        return {
            'success': True,
            'filename': file.filename,
            'size': len(data),
            'url': file_service.get_file_url(codigo, folder, file.filename),
            'message': f"✅ Archivo {file.filename} subido"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{codigo}/{folder}")
async def list_files(codigo: str, folder: str):
    """
    Lista archivos en una carpeta
    
    Usado por: Panel web (listar archivos disponibles)
    """
    try:
        files = file_service.list_files(codigo, folder)
        return {
            'success': True,
            'files': files,
            'count': len(files)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{codigo}/{folder}/{filename}")
async def delete_file(codigo: str, folder: str, filename: str):
    """
    Elimina un archivo
    
    Usado por: Panel web (eliminar archivos)
    """
    try:
        success = file_service.delete_file(codigo, folder, filename)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Archivo {filename} no encontrado"
            )
        
        return {
            'success': True,
            'message': f"✅ Archivo {filename} eliminado"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/storage/info")
async def get_storage_info():
    """
    Obtiene información del storage
    
    Usado por: Panel web (estadísticas)
    """
    try:
        info = file_service.get_storage_info()
        return {
            'success': True,
            'storage': info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
