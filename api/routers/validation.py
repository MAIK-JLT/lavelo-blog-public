"""
Router de Validation para FastAPI
Endpoints para validación de fases del workflow
"""
from fastapi import APIRouter, HTTPException, status, Request
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
async def validate_phase(request: ValidatePhaseRequest, http_request: Request):
    """
    Valida una fase y ejecuta la acción correspondiente
    
    Usado por: Panel web (botón VALIDATE)
    """
    try:
        user_id = http_request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        result = await validation_service.validate_phase(
            request.codigo,
            request.current_state,
            request.redes,
            user_id=user_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/reset-phases")
async def reset_phases(request: ResetPhasesRequest, http_request: Request):
    """
    Resetea fases dependientes cuando se edita una fase validada
    
    Usado por: Panel web (al guardar cambios en fase validada)
    """
    try:
        user_id = http_request.session.get('user_id')
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
        result = await validation_service.reset_dependent_phases(
            request.codigo,
            request.edited_phase,
            user_id=user_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
