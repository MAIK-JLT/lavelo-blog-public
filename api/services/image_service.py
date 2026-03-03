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
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import asyncio

# Cargar variables de entorno (producción primero, luego fallback local)
default_env = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

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
    
    async def generate_image(self, codigo: str, num_images: int = 2, user_id: int = None) -> Dict:
        """
        Genera imagen base usando Fal.ai SeaDream 4.0
        Soporta hasta 2 imágenes de referencia
        
        Usado por:
        - Panel Web: Botón "Generar Imagen"
        - MCP: generate_image()
        """
        print(f"\n🎨 === GENERANDO IMAGEN BASE PARA {codigo} ===")
        
        if user_id:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

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
        result = await asyncio.to_thread(
            fal_client.subscribe,
            "fal-ai/bytedance/seedream/v4/text-to-image",
            arguments=arguments
        )
        
        print(f"✅ Generación completada!")
        
        # 6. Procesar resultados
        if not result or 'images' not in result or len(result['images']) == 0:
            raise Exception('No se generaron imágenes')
        
        generated_images = []
        
        for idx, image_data in enumerate(result['images'], 1):
            image_url = image_data.get('url')
            
            if image_url:
                # Descargar imagen
                response = await asyncio.to_thread(requests.get, image_url)
                image_bytes = response.content
                
                # Guardar localmente
                # Si num_images == 1, guardar directo como imagen_base.png
                # Si num_images > 1, guardar variaciones numeradas
                if num_images == 1:
                    filename = f"{codigo}_imagen_base.png"
                else:
                    filename = f"{codigo}_imagen_base_{idx}.png"
                
                self.file_service.save_binary_file(codigo, 'imagenes', filename, image_bytes)
                
                generated_images.append({
                    'filename': filename,
                    'url': image_url,
                    'index': idx
                })
                
                print(f"  💾 Guardada: {filename}")

        # Copiar la primera variación como imagen base si se generaron variaciones
        if generated_images and num_images > 1:
            try:
                first_filename = f"{codigo}_imagen_base_1.png"
                first_bytes = self.file_service.read_binary_file(codigo, 'imagenes', first_filename)
                if first_bytes:
                    self.file_service.save_binary_file(codigo, 'imagenes', f"{codigo}_imagen_base.png", first_bytes)
            except Exception as e:
                print(f"⚠️ No se pudo copiar imagen base: {e}")

        # Si solo se generó imagen base, limpiar metadata/variaciones anteriores
        if num_images == 1:
            try:
                imagenes = self.file_service.list_files(codigo, 'imagenes')
                for fname in imagenes:
                    if fname.startswith(f"{codigo}_imagen_base_") and fname.endswith(".png"):
                        self.file_service.delete_file(codigo, 'imagenes', fname)
                self.file_service.delete_file(codigo, 'textos', f"{codigo}_imagen_variations.json")
            except Exception as e:
                print(f"⚠️ No se pudieron limpiar variaciones anteriores: {e}")
        
        # 7. Guardar metadata de variaciones
        if generated_images and num_images > 1:
            variations = [img["filename"] for img in generated_images]
            metadata = {
                "generated": variations,
                "selected": f"{codigo}_imagen_base_1.png"
            }
            metadata_filename = f"{codigo}_imagen_variations.json"
            try:
                file_service.save_file(codigo, "textos", metadata_filename, json.dumps(metadata, indent=2))
            except Exception as e:
                print(f"⚠️ No se pudo guardar metadata de variaciones: {e}")

        # 8. Actualizar checkbox en BD y resetear fases posteriores
        if generated_images:
            db_service.update_post(codigo, {
                'imagen_base_png': True,
                'instagram_1x1_png': False,
                'instagram_stories_9x16_png': False,
                'linkedin_16x9_png': False,
                'twitter_16x9_png': False,
                'facebook_16x9_png': False,
                'script_video_base_txt': False,
                'video_base_mp4': False,
                'feed_16x9_mp4': False,
                'stories_9x16_mp4': False,
                'shorts_9x16_mp4': False,
                'tiktok_9x16_mp4': False,
                'estado': 'IMAGE_BASE_AWAITING'
            }, user_id=user_id)
            print(f"✅ Checkbox imagen_base actualizado y fases posteriores reseteadas")
        
        return {
            'success': True,
            'message': f'{len(generated_images)} imágenes generadas correctamente',
            'images': generated_images,
            'references_used': len(reference_images)
        }
    
    async def format_images(self, codigo: str, user_id: int = None) -> Dict:
        """
        Formatea imagen base para diferentes redes sociales usando Cloudinary AI
        (crop inteligente con detección de sujetos)
        
        Usado por:
        - Panel Web: Validar Fase 4 (IMAGE_BASE_AWAITING)
        """
        import cloudinary
        import cloudinary.uploader
        from io import BytesIO
        import tempfile
        import requests
        
        print(f"\n🖼️ === FORMATEANDO IMÁGENES CON CLOUDINARY AI ===")
        
        if user_id:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

        # 1. Leer imagen base
        base_filename = f"{codigo}_imagen_base.png"
        image_bytes = self.file_service.read_binary_file(codigo, 'imagenes', base_filename)
        
        if not image_bytes:
            raise Exception(f'Imagen base no encontrada: {base_filename}')
        
        print(f"📥 Imagen base cargada: {len(image_bytes)} bytes")
        
        # 2. Subir a Cloudinary
        print(f"📤 Subiendo a Cloudinary...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(image_bytes)
        
        try:
            upload_result = cloudinary.uploader.upload(
                tmp_path,
                resource_type='image',
                public_id=f"lavelo_blog/{codigo}_imagen_base",
                overwrite=True
            )
            
            public_id = upload_result['public_id']
            print(f"✅ Subida a Cloudinary: {public_id}")
            
            # 3. Definir formatos con crop inteligente (gravity: auto:subject)
            formats = {
                'instagram_1x1': {
                    'width': 1080, 'height': 1080,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'instagram_stories_9x16': {
                    'width': 1080, 'height': 1920,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'linkedin_16x9': {
                    'width': 1200, 'height': 627,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'twitter_16x9': {
                    'width': 1200, 'height': 675,
                    'crop': 'fill', 'gravity': 'auto:subject'
                },
                'facebook_16x9': {
                    'width': 1200, 'height': 630,
                    'crop': 'fill', 'gravity': 'auto:subject'
                }
            }
            
            formatted = []
            
            # 4. Generar cada formato
            for name, specs in formats.items():
                print(f"  🎨 Generando {name}...")
                
                try:
                    # Generar transformación explícita en Cloudinary
                    explicit_result = cloudinary.uploader.explicit(
                        public_id,
                        type='upload',
                        resource_type='image',
                        eager=[{
                            'width': specs['width'],
                            'height': specs['height'],
                            'crop': specs['crop'],
                            'gravity': specs['gravity'],
                            'quality': 'auto:good',
                            'fetch_format': 'auto'
                        }]
                    )
                    
                    # Obtener URL de la transformación
                    transformed_url = explicit_result['eager'][0]['secure_url']
                    
                    # Descargar imagen transformada
                    response = requests.get(transformed_url)
                    transformed_bytes = response.content
                    
                    # Guardar en storage
                    filename = f"{codigo}_{name}.png"
                    self.file_service.save_binary_file(codigo, 'imagenes', filename, transformed_bytes)
                    
                    # Actualizar checkbox en BD
                    checkbox_field = f'{name}_png'
                    db_service.update_post(codigo, {checkbox_field: True}, user_id=user_id)
                    
                    formatted.append(filename)
                    print(f"    ✅ {filename} ({specs['width']}x{specs['height']})")
                    
                except Exception as e:
                    print(f"    ❌ Error generando {name}: {e}")
            
            # Limpiar archivo temporal
            import os
            os.unlink(tmp_path)
            
            return {
                'success': True,
                'formatted': formatted,
                'message': f'✅ {len(formatted)} formatos generados con Cloudinary AI'
            }
            
        except Exception as e:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise Exception(f'Error en Cloudinary: {str(e)}')
    
    async def upload_manual_image(self, codigo: str, filename: str, image_bytes: bytes, user_id: int = None) -> Dict:
        """
        Sube una imagen manualmente (alternativa a generación con IA)
        
        Usado por:
        - Panel Web: Botón "Subir Imagen"
        """
        if user_id:
            post = db_service.get_post_by_codigo(codigo, user_id=user_id)
            if not post:
                raise Exception("Post no encontrado")

        # Guardar imagen
        self.file_service.save_binary_file(codigo, 'imagenes', filename, image_bytes)
        
        # Si es imagen_base, actualizar checkbox
        if 'imagen_base' in filename:
            db_service.update_post(codigo, {'imagen_base_png': True}, user_id=user_id)
        
        return {
            'success': True,
            'filename': filename,
            'size': len(image_bytes),
            'message': f'✅ Imagen {filename} subida'
        }

# Instancia global
image_service = ImageService()
