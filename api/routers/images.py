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

router = APIRouter(
    prefix="/api",
    tags=["Images"]
)

class GenerateImageRequest(BaseModel):
    codigo: str
    num_images: int = 4

class FormatImagesRequest(BaseModel):
    codigo: str

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
        
        # Guardar metadata de referencias si existen
        if reference_info:
            metadata = {
                'references': reference_info,
                'selections': selections_dict
            }
            metadata_filename = f"{codigo}_referencias_metadata.json"
            file_service.save_file(codigo, 'textos', metadata_filename, json.dumps(metadata, indent=2))
            print(f"💾 Metadata guardada: {metadata_filename}")
        
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
