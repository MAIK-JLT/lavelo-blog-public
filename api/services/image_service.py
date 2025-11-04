"""
Servicio de generación y formateo de imágenes
Usado por: MCP Server, Panel Web, API REST
"""
from typing import List, Optional, Dict
import sys
import os
import json
import base64
import requests
import fal_client

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service
from services.file_service import file_service

class ImageService:
    """Servicio para generar y formatear imágenes"""
    
    def __init__(self):
        self.file_service = file_service
        # Configurar Fal.ai
        fal_key = os.getenv('FAL_KEY')
        if fal_key:
            os.environ['FAL_KEY'] = fal_key
    
    async def generate_image(self, codigo: str, num_images: int = 4) -> Dict:
        """
        Genera imagen base usando Fal.ai SeaDream 4.0
        Soporta hasta 2 imágenes de referencia
        
        Usado por:
        - Panel Web: Botón "Generar Imagen"
        - MCP: generate_image()
        """
        print(f"\n🎨 === GENERANDO IMAGEN BASE PARA {codigo} ===")
        
        # 1. Leer prompt
        prompt_filename = f"{codigo}_prompt_imagen.txt"
        prompt = self.file_service.read_file(codigo, 'textos', prompt_filename)
        
        if not prompt:
            raise Exception('Prompt no encontrado. Completa Fase 3 primero.')
        
        print(f"📝 Prompt: {prompt[:100]}...")
        
        # 2. Leer metadata de referencias (si existen)
        metadata_filename = f"{codigo}_referencias_metadata.json"
        metadata_text = self.file_service.read_file(codigo, 'textos', metadata_filename)
        
        reference_images = []
        if metadata_text:
            metadata = json.loads(metadata_text)
            referencias = metadata.get('references', [])
            
            print(f"📸 Referencias encontradas: {len(referencias)}")
            
            # 3. Cargar imágenes de referencia y convertir a base64
            for ref in referencias:
                try:
                    # Leer imagen
                    image_bytes = self.file_service.read_binary_file(codigo, 'imagenes', ref['filename'])
                    
                    if image_bytes:
                        # Convertir a base64 data URL
                        base64_image = base64.b64encode(image_bytes).decode('utf-8')
                        data_url = f"data:image/png;base64,{base64_image}"
                        
                        reference_images.append({
                            'image_url': data_url,
                            'weight': ref.get('influence', 0.3)
                        })
                        print(f"  ✅ Referencia cargada: {ref['filename']} (peso: {ref.get('influence', 0.3)})")
                except Exception as e:
                    print(f"  ⚠️ Error cargando referencia {ref['filename']}: {e}")
        
        # 4. Preparar argumentos para SeaDream 4.0
        arguments = {
            "prompt": prompt,
            "image_size": "square_hd",  # 1024x1024
            "num_inference_steps": 28,
            "num_images": num_images,
            "enable_safety_checker": False
        }
        
        # Agregar referencias si existen
        if reference_images:
            arguments["reference_images"] = reference_images
            print(f"🖼️  Usando {len(reference_images)} imágenes de referencia")
        
        print(f"🚀 Llamando a Fal.ai SeaDream 4.0...")
        
        # 5. Llamar a Fal.ai
        result = fal_client.subscribe(
            "fal-ai/bytedance/seedream/v4/text-to-image",
            arguments=arguments
        )
        
        print(f"✅ Generación completada!")
        
        # 6. Procesar resultados
        if not result or 'images' not in result or len(result['images']) == 0:
            raise Exception('No se generaron imágenes')
        
        # Verificar si ya existe imagen_base.png
        base_exists = self.file_service.file_exists(codigo, 'imagenes', f"{codigo}_imagen_base.png")
        
        generated_images = []
        
        for idx, image_data in enumerate(result['images'], 1):
            image_url = image_data.get('url')
            
            if image_url:
                # Descargar imagen
                response = requests.get(image_url)
                image_bytes = response.content
                
                # Guardar localmente
                # Si ya existe imagen_base.png, guardar todas como variaciones (_2, _3, _4, _5)
                if base_exists:
                    filename = f"{codigo}_imagen_base_{idx + 1}.png"
                else:
                    # Primera generación: guardar como _base.png, _base_2.png, etc.
                    filename = f"{codigo}_imagen_base_{idx}.png" if idx > 1 else f"{codigo}_imagen_base.png"
                
                self.file_service.save_binary_file(codigo, 'imagenes', filename, image_bytes)
                
                generated_images.append({
                    'filename': filename,
                    'url': image_url,
                    'index': idx
                })
                
                print(f"  💾 Guardada: {filename}")
        
        # 7. Actualizar checkbox en BD
        if generated_images:
            db_service.update_post(codigo, {'imagen_base_png': True})
            print(f"✅ Checkbox imagen_base actualizado")
        
        return {
            'success': True,
            'message': f'{len(generated_images)} imágenes generadas correctamente',
            'images': generated_images,
            'references_used': len(reference_images)
        }
    
    async def format_images(self, codigo: str) -> Dict:
        """
        Formatea imagen base para diferentes redes sociales
        
        Usado por:
        - Panel Web: Validar Fase 4 (IMAGE_BASE_AWAITING)
        """
        from PIL import Image
        from io import BytesIO
        
        # Leer imagen base
        base_filename = f"{codigo}_imagen_base.png"
        image_bytes = self.file_service.read_binary_file(codigo, 'imagenes', base_filename)
        
        if not image_bytes:
            raise Exception(f'Imagen base no encontrada: {base_filename}')
        
        # Abrir imagen con Pillow
        img = Image.open(BytesIO(image_bytes))
        
        # Formatos para redes sociales
        formats = {
            'instagram_1x1': (1080, 1080),
            'instagram_stories_9x16': (1080, 1920),
            'linkedin_16x9': (1200, 627),
            'twitter_16x9': (1200, 675),
            'facebook_16x9': (1200, 630)
        }
        
        formatted = []
        
        for name, size in formats.items():
            # Resize manteniendo aspecto y crop al centro
            img_resized = img.copy()
            img_resized.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Crear imagen final con tamaño exacto
            final_img = Image.new('RGB', size, (255, 255, 255))
            offset = ((size[0] - img_resized.width) // 2, (size[1] - img_resized.height) // 2)
            final_img.paste(img_resized, offset)
            
            # Guardar
            output = BytesIO()
            final_img.save(output, format='PNG')
            output_bytes = output.getvalue()
            
            filename = f"{codigo}_{name}.png"
            self.file_service.save_binary_file(codigo, 'imagenes', filename, output_bytes)
            
            # Actualizar checkbox en BD
            checkbox_field = f'{name}_png'
            db_service.update_post(codigo, {checkbox_field: True})
            
            formatted.append(filename)
            print(f"  ✅ {filename} generado ({size[0]}x{size[1]})")
        
        return {
            'success': True,
            'formatted': formatted,
            'message': f'✅ {len(formatted)} formatos generados'
        }
    
    async def upload_manual_image(self, codigo: str, filename: str, image_bytes: bytes) -> Dict:
        """
        Sube una imagen manualmente (alternativa a generación con IA)
        
        Usado por:
        - Panel Web: Botón "Subir Imagen"
        """
        # Guardar imagen
        self.file_service.save_binary_file(codigo, 'imagenes', filename, image_bytes)
        
        # Si es imagen_base, actualizar checkbox
        if 'imagen_base' in filename:
            db_service.update_post(codigo, {'imagen_base_png': True})
        
        return {
            'success': True,
            'filename': filename,
            'size': len(image_bytes),
            'message': f'✅ Imagen {filename} subida'
        }

# Instancia global
image_service = ImageService()
