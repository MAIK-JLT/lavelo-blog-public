"""
Router de Videos para FastAPI
Endpoints para generación y formateo de videos
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.video_service import video_service

router = APIRouter(
    prefix="/api",
    tags=["Videos"]
)

class GenerateVideoTextRequest(BaseModel):
    prompt: str
    resolution: str = '720p'

class GenerateVideoImageRequest(BaseModel):
    prompt: str
    image_url: str
    resolution: str = '720p'

class GenerateVideoBaseRequest(BaseModel):
    codigo: str

class FormatVideosRequest(BaseModel):
    codigo: str

@router.post("/generate-video-text")
async def generate_video_text(request: GenerateVideoTextRequest):
    """
    Genera video desde texto usando Fal.ai SeeDance 1.0 Pro
    
    Usado por: Falai playground, tests
    """
    try:
        result = await video_service.generate_video_from_text(request.prompt, request.resolution)
        
        # Guardar en test_results para pruebas
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'falai', 'test_results')
        os.makedirs(results_dir, exist_ok=True)
        
        filename = f"test_{timestamp}_video.mp4"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(result['video_bytes'])
        
        return {
            'success': True,
            'video_url': result['video_url'],
            'local_path': filepath,
            'filename': filename,
            'duration': result['duration'],
            'resolution': result['resolution'],
            'size_mb': result['size_mb']
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate-video-image")
async def generate_video_image(request: GenerateVideoImageRequest):
    """
    Genera video desde imagen usando Fal.ai SeeDance 1.0 Pro
    
    Usado por: Falai playground, tests
    """
    try:
        result = await video_service.generate_video_from_image(
            request.prompt, 
            request.image_url, 
            request.resolution
        )
        
        # Guardar en test_results para pruebas
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'falai', 'test_results')
        os.makedirs(results_dir, exist_ok=True)
        
        filename = f"test_{timestamp}_video.mp4"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(result['video_bytes'])
        
        return {
            'success': True,
            'video_url': result['video_url'],
            'local_path': filepath,
            'filename': filename,
            'duration': result['duration'],
            'resolution': result['resolution'],
            'size_mb': result['size_mb']
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate-video-base")
async def generate_video_base(request: GenerateVideoBaseRequest):
    """
    Genera video base para un post usando script de video
    
    Usado por: Panel web (validar Fase 6)
    """
    try:
        result = await video_service.generate_video_base(request.codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/format-videos")
async def format_videos(request: FormatVideosRequest):
    """
    Formatea video base para diferentes redes sociales
    
    Usado por: Panel web (validar Fase 7)
    """
    try:
        result = await video_service.format_videos(request.codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
