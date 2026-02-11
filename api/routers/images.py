"""
Router de Images para FastAPI
Endpoints para generación y formateo de imágenes
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.image_service import image_service
from services.file_service import file_service
import db_service

router = APIRouter(
    prefix="/api",
    tags=["Images"]
)

class GenerateImageRequest(BaseModel):
    codigo: str
    num_images: int = 2

class FormatImagesRequest(BaseModel):
    codigo: str

class SelectBaseImageRequest(BaseModel):
    codigo: str
    filename: str

@router.post("/generate-image")
async def generate_image(request: GenerateImageRequest):
    """
    Genera imagen base usando Fal.ai SeaDream 4.0
    Soporta hasta 2 imágenes de referencia
    
    Usado por: Panel web (validar Fase 3)
    """
    try:
        result = await image_service.generate_image(request.codigo, request.num_images)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/format-images")
async def format_images(request: FormatImagesRequest):
    """
    Formatea imagen base para diferentes redes sociales
    
    Usado por: Panel web (validar Fase 4)
    """
    try:
        result = await image_service.format_images(request.codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/upload-image/{codigo}")
async def upload_image(codigo: str, file: UploadFile = File(...)):
    """
    Sube una imagen manualmente (alternativa a generación con IA)
    
    Usado por: Panel web (subir imagen manual)
    """
    try:
        # Leer contenido del archivo
        image_bytes = await file.read()
        
        result = await image_service.upload_manual_image(codigo, file.filename, image_bytes)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/select-base-image")
async def select_base_image(request: SelectBaseImageRequest):
    """
    Selecciona una variación como imagen base (copia a *_imagen_base.png)
    
    Usado por: Panel web (fase 4)
    """
    try:
        codigo = request.codigo
        filename = request.filename

        if not filename or not filename.endswith(".png"):
            raise Exception("Filename inválido")

        # Leer variación
        image_bytes = file_service.read_binary_file(codigo, "imagenes", filename)
        if not image_bytes:
            raise Exception("Imagen no encontrada")

        # Guardar como imagen base
        base_filename = f"{codigo}_imagen_base.png"
        file_service.save_binary_file(codigo, "imagenes", base_filename, image_bytes)

        # Actualizar metadata de variaciones
        metadata_filename = f"{codigo}_imagen_variations.json"
        metadata_text = file_service.read_file(codigo, "textos", metadata_filename)
        if metadata_text:
            try:
                metadata = json.loads(metadata_text)
                metadata["selected"] = base_filename
                file_service.save_file(codigo, "textos", metadata_filename, json.dumps(metadata, indent=2))
            except Exception:
                pass

        # Al cambiar imagen base, resetear formatos y fases posteriores
        db_service.update_post(codigo, {
            "imagen_base_png": True,
            "instagram_1x1_png": False,
            "instagram_stories_9x16_png": False,
            "linkedin_16x9_png": False,
            "twitter_16x9_png": False,
            "facebook_16x9_png": False,
            "script_video_base_txt": False,
            "video_base_mp4": False,
            "feed_16x9_mp4": False,
            "stories_9x16_mp4": False,
            "shorts_9x16_mp4": False,
            "tiktok_9x16_mp4": False,
            "estado": "IMAGE_BASE_AWAITING"
        })

        return {"success": True, "message": "Imagen base actualizada"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/improve-prompt-visual")
async def improve_prompt_visual(
    codigo: str = Form(...),
    prompt_original: str = Form(...),
    selections: str = Form("{}"),
    ref1: Optional[UploadFile] = File(None),
    ref1_influence: Optional[float] = Form(0.5),
    ref2: Optional[UploadFile] = File(None),
    ref2_influence: Optional[float] = Form(0.5)
):
    """
    Mejora el prompt con selecciones visuales e imágenes de referencia
    
    Usado por: Prompt Builder (prompt_builder.html)
    """
    try:
        from services.content_service import ContentService
        from services.file_service import file_service
        import db_service
        
        content_service = ContentService()
        
        print(f"🎨 Mejorando prompt visual para post {codigo}")
        print(f"📝 Prompt original: {prompt_original[:100]}...")
        
        # Parsear selecciones
        selections_dict = json.loads(selections) if selections else {}
        print(f"🎯 Selecciones: {selections_dict}")
        
        # Procesar imágenes de referencia
        reference_info = []
        
        for ref_num, (ref_file, influence) in enumerate([(ref1, ref1_influence), (ref2, ref2_influence)], 1):
            if ref_file and ref_file.filename:
                # Leer imagen
                ref_bytes = await ref_file.read()
                
                # Guardar en storage local
                ref_filename = f"{codigo}_referencia_{ref_num}.png"
                file_service.save_binary_file(codigo, 'imagenes', ref_filename, ref_bytes)
                
                influence_labels = {
                    0.5: 'Inspiración (mood/colores)',
                    1.0: 'Guía (estructura similar)',
                    2.0: 'Exacta (replicar elemento)'
                }
                
                reference_info.append({
                    'filename': ref_filename,
                    'influence': influence,
                    'label': influence_labels.get(influence, f'Influencia: {influence}')
                })
                
                print(f"  📸 Referencia {ref_num}: {ref_filename} (influencia: {influence})")
        
        # Construir prompt mejorado con Claude
        improved_prompt = await content_service.improve_prompt_with_visual_selections(
            prompt_original,
            selections_dict,
            reference_info
        )
        
        # Guardar prompt mejorado
        prompt_filename = f"{codigo}_prompt_imagen.txt"
        file_service.save_file(codigo, 'textos', prompt_filename, improved_prompt)
        print(f"💾 Prompt mejorado guardado: {prompt_filename}")

        # Limpiar imágenes/variaciones anteriores al cambiar prompt
        try:
            imagenes = file_service.list_files(codigo, 'imagenes')
            for fname in imagenes:
                if fname.startswith(f"{codigo}_imagen_base") and fname.endswith(".png"):
                    file_service.delete_file(codigo, 'imagenes', fname)
            file_service.delete_file(codigo, 'textos', f"{codigo}_imagen_variations.json")
            print("🧹 Variaciones anteriores eliminadas")
        except Exception as e:
            print(f"⚠️ No se pudieron limpiar variaciones: {e}")
        
        # Guardar metadata de referencias si existen
        if reference_info:
            metadata = {
                'references': reference_info,
                'selections': selections_dict
            }
            metadata_filename = f"{codigo}_referencias_metadata.json"
            file_service.save_file(codigo, 'textos', metadata_filename, json.dumps(metadata, indent=2))
            print(f"💾 Metadata guardada: {metadata_filename}")
        
        # Resetear fases de imagen para regenerar con nuevo prompt
        print(f"🔄 Reseteando fases de imagen para regenerar...")
        post = db_service.get_post_by_codigo(codigo)
        
        if post and post.get('estado') not in ['DRAFT', 'BASE_TEXT_AWAITING', 'ADAPTED_TEXTS_AWAITING', 'IMAGE_PROMPT_AWAITING']:
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
            'improved_prompt': improved_prompt,
            'references_saved': len(reference_info),
            'metadata': reference_info
        }
        
    except Exception as e:
        print(f"❌ Error mejorando prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
