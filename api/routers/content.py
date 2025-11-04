"""
Router de Content para FastAPI
Endpoints para generación de contenido con Claude
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Optional
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.content_service import content_service

router = APIRouter(
    prefix="/api",
    tags=["Content"]
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict]] = []

class GenerateAdaptedTextsRequest(BaseModel):
    codigo: str
    redes: Dict[str, bool]

class GeneratePromptRequest(BaseModel):
    codigo: str

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat con Claude usando herramientas MCP
    
    Usado por: Panel web (chat flotante)
    """
    try:
        result = await content_service.chat(request.message, request.history)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate-adapted-texts")
async def generate_adapted_texts(request: GenerateAdaptedTextsRequest):
    """
    Genera textos adaptados para redes sociales
    
    Usado por: Panel web (validar Fase 1)
    """
    try:
        result = await content_service.generate_adapted_texts(request.codigo, request.redes)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate-image-prompt")
async def generate_image_prompt(request: GeneratePromptRequest):
    """
    Genera prompt para imagen usando Claude
    
    Usado por: Panel web (validar Fase 2)
    """
    try:
        result = await content_service.generate_image_prompt(request.codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate-video-script")
async def generate_video_script(request: GeneratePromptRequest):
    """
    Genera script para video usando Claude
    
    Usado por: Panel web (validar Fase 5)
    """
    try:
        result = await content_service.generate_video_script(request.codigo)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
