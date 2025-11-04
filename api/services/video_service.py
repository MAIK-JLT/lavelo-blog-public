"""
Servicio de generación y formateo de videos
Usado por: MCP Server, Panel Web, API REST
"""
from typing import List, Optional, Dict
import sys
import os
import requests
import fal_client
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service
from services.file_service import file_service

class VideoService:
    """Servicio para generar y formatear videos"""
    
    def __init__(self):
        self.file_service = file_service
        # Configurar Fal.ai
        fal_key = os.getenv('FAL_KEY')
        if fal_key:
            os.environ['FAL_KEY'] = fal_key
    
    async def generate_video_from_text(self, prompt: str, resolution: str = '720p') -> Dict:
        """
        Genera video desde texto usando Fal.ai SeeDance 1.0 Pro
        
        Usado por:
        - Panel Web: Test de generación
        - Falai: Playground
        """
        print(f"\n🎬 === GENERANDO TEXT-TO-VIDEO ===")
        print(f"📝 Prompt: {prompt[:100]}...")
        print(f"📐 Resolución: {resolution}")
        
        # Configurar dimensiones
        if resolution == '1024p':
            width, height = 1024, 1024
        else:  # 720p por defecto
            width, height = 1280, 720
        
        # Llamar a Fal.ai
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedance/v1/pro/text-to-video",
            arguments={
                "prompt": prompt,
                "video_size": {
                    "width": width,
                    "height": height
                }
            },
            with_logs=True,
            on_queue_update=lambda update: print(f"  ⏳ Status: {getattr(update, 'status', 'processing')}")
        )
        
        print(f"✅ Video generado!")
        video_url = result['video']['url']
        
        # Descargar video
        response = requests.get(video_url)
        video_bytes = response.content
        
        return {
            'success': True,
            'video_url': video_url,
            'video_bytes': video_bytes,
            'duration': result.get('timings', {}).get('inference', 0),
            'resolution': f"{width}x{height}",
            'size_mb': len(video_bytes) / (1024 * 1024)
        }
    
    async def generate_video_from_image(self, prompt: str, image_url: str, resolution: str = '720p') -> Dict:
        """
        Genera video desde imagen usando Fal.ai SeeDance 1.0 Pro
        
        Usado por:
        - Panel Web: Test de generación
        - Falai: Playground
        """
        print(f"\n🎬 === GENERANDO IMAGE-TO-VIDEO ===")
        print(f"📝 Prompt: {prompt[:100]}...")
        print(f"🖼️  Imagen: {image_url[:50]}...")
        print(f"📐 Resolución: {resolution}")
        
        # Configurar dimensiones
        if resolution == '1024p':
            width, height = 1024, 1024
        else:  # 720p por defecto
            width, height = 1280, 720
        
        # Llamar a Fal.ai
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedance/v1/pro/image-to-video",
            arguments={
                "prompt": prompt,
                "image_url": image_url,
                "video_size": {
                    "width": width,
                    "height": height
                }
            },
            with_logs=True,
            on_queue_update=lambda update: print(f"  ⏳ Status: {getattr(update, 'status', 'processing')}")
        )
        
        print(f"✅ Video generado!")
        video_url = result['video']['url']
        
        # Descargar video
        response = requests.get(video_url)
        video_bytes = response.content
        
        return {
            'success': True,
            'video_url': video_url,
            'video_bytes': video_bytes,
            'duration': result.get('timings', {}).get('inference', 0),
            'resolution': f"{width}x{height}",
            'size_mb': len(video_bytes) / (1024 * 1024)
        }
    
    async def generate_video_base(self, codigo: str) -> Dict:
        """
        Genera video base para un post usando script de video
        
        Usado por:
        - Panel Web: Validar Fase 6 (VIDEO_PROMPT_AWAITING)
        """
        # Leer script de video
        script_filename = f"{codigo}_script_video.txt"
        script = self.file_service.read_file(codigo, 'textos', script_filename)
        
        if not script:
            raise Exception('Script de video no encontrado. Completa Fase 5 primero.')
        
        # Leer imagen base para usar como referencia
        base_image = f"{codigo}_imagen_base.png"
        image_bytes = self.file_service.read_binary_file(codigo, 'imagenes', base_image)
        
        if not image_bytes:
            raise Exception('Imagen base no encontrada. Completa Fase 4 primero.')
        
        # Por ahora, generar desde texto (en futuro podría usar imagen)
        result = await self.generate_video_from_text(script, resolution='720p')
        
        # Guardar video base
        filename = f"{codigo}_video_base.mp4"
        self.file_service.save_binary_file(codigo, 'videos', filename, result['video_bytes'])
        
        # Actualizar checkbox en BD
        db_service.update_post(codigo, {'video_base_mp4': True})
        
        print(f"💾 Video base guardado: {filename}")
        
        return {
            'success': True,
            'filename': filename,
            'video_url': result['video_url'],
            'duration': result['duration'],
            'size_mb': result['size_mb'],
            'message': f'✅ Video base generado'
        }
    
    async def format_videos(self, codigo: str) -> Dict:
        """
        Formatea video base para diferentes redes sociales usando FFmpeg
        
        Usado por:
        - Panel Web: Validar Fase 7 (VIDEO_BASE_AWAITING)
        """
        import subprocess
        
        # Leer video base
        base_filename = f"{codigo}_video_base.mp4"
        base_path = self.file_service._get_file_path(codigo, 'videos', base_filename)
        
        if not base_path.exists():
            raise Exception(f'Video base no encontrado: {base_filename}')
        
        # Formatos para redes sociales
        formats = {
            'feed_16x9': {'width': 1920, 'height': 1080, 'crop': 'center'},
            'stories_9x16': {'width': 1080, 'height': 1920, 'crop': 'center'},
            'shorts_9x16': {'width': 1080, 'height': 1920, 'crop': 'center'},
            'tiktok_9x16': {'width': 1080, 'height': 1920, 'crop': 'center'}
        }
        
        formatted = []
        
        for name, specs in formats.items():
            output_filename = f"{codigo}_{name}.mp4"
            output_path = self.file_service._get_file_path(codigo, 'videos', output_filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Comando FFmpeg para resize y crop
            cmd = [
                'ffmpeg',
                '-i', str(base_path),
                '-vf', f"scale={specs['width']}:{specs['height']}:force_original_aspect_ratio=increase,crop={specs['width']}:{specs['height']}",
                '-c:a', 'copy',
                '-y',  # Sobrescribir si existe
                str(output_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Actualizar checkbox en BD
                checkbox_field = f'{name}_mp4'
                db_service.update_post(codigo, {checkbox_field: True})
                
                formatted.append(output_filename)
                print(f"  ✅ {output_filename} generado ({specs['width']}x{specs['height']})")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Error formateando {name}: {e.stderr.decode()}")
        
        return {
            'success': True,
            'formatted': formatted,
            'message': f'✅ {len(formatted)} formatos de video generados'
        }

# Instancia global
video_service = VideoService()
