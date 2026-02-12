"""
Router de Auth para FastAPI
Login propio (email/password) + settings del usuario
"""
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_BCRYPT_PASSWORD_BYTES = 72

def _ensure_password_length(password: str):
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña no puede estar vacía"
        )
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es demasiado larga (máximo 72 bytes)"
        )

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SettingsRequest(BaseModel):
    system_prompt: str | None = None

@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    existing = db_service.get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ya registrado"
        )

    _ensure_password_length(req.password)
    password_hash = pwd_context.hash(req.password)
    user = db_service.create_user(req.email, password_hash, req.name)
    db_service.update_user(user.id, {"last_login": datetime.utcnow()})

    # Si es el primer usuario, asignar posts existentes sin owner
    try:
        if db_service.get_user_count() == 1:
            db_service.claim_unowned_posts(user.id)
    except Exception:
        pass

    request.session['user_id'] = user.id
    return {"success": True, "user": user.to_dict()}

@router.post("/login")
async def login(req: LoginRequest, request: Request):
    user = db_service.get_user_by_email(req.email)
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    _ensure_password_length(req.password)
    if not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    db_service.update_user(user.id, {"last_login": datetime.utcnow()})
    request.session['user_id'] = user.id
    return {"success": True, "user": user.to_dict()}

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True}

@router.get("/me")
async def me(request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user = db_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return {"success": True, "user": user.to_dict()}

@router.get("/settings")
async def get_settings(request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user = db_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return {"success": True, "system_prompt": user.system_prompt or ""}

@router.post("/settings")
async def update_settings(req: SettingsRequest, request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user = db_service.update_user(user_id, {"system_prompt": req.system_prompt or ""})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {"success": True}
