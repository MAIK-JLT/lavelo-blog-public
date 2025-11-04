"""
Router de Validation para FastAPI
Endpoints para validación de fases del workflow
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.validation_service import validation_service

router = APIRouter(
    prefix="/api",
    tags=["Validation"]
)

class ValidatePhaseRequest(BaseModel):
    codigo: str
    current_state: str
    redes: Dict[str, bool] = {}

class ResetPhasesRequest(BaseModel):
    codigo: str
    edited_phase: int

@router.post("/validate-phase")
async def validate_phase(request: ValidatePhaseRequest):
    """
    Valida una fase y ejecuta la acción correspondiente
    
    Usado por: Panel web (botón VALIDATE)
    """
    try:
        result = await validation_service.validate_phase(
            request.codigo,
            request.current_state,
            request.redes
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/reset-phases")
async def reset_phases(request: ResetPhasesRequest):
    """
    Resetea fases dependientes cuando se edita una fase validada
    
    Usado por: Panel web (al guardar cambios en fase validada)
    """
    try:
        result = await validation_service.reset_dependent_phases(
            request.codigo,
            request.edited_phase
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
