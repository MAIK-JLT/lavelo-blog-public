from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
import logging
import time

# Cargar variables de entorno
# 1) Usa ENV_FILE o LAVELO_ENV_FILE si están definidos (p. ej. /var/www/vhosts/<dominio>/private/.env)
# 2) Si no, hace fallback al .env del repo (../.env) para desarrollo local
default_env = os.path.join(os.path.dirname(__file__), '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler('/tmp/lavelo_api.log')  # Archivo
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lavelo Blog API",
    description="API para gestión automatizada de contenido de triatlón",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Session Middleware (debe ir ANTES de CORS)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
    session_cookie="lavelo_session",
    max_age=30 * 24 * 60 * 60,  # 30 días
    same_site="lax",
    https_only=False  # True en producción
)

# CORS - Configuración según entorno
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Permitir todos los orígenes en desarrollo, específicos en producción
allowed_origins = [
    "https://blog.lavelo.es",
    "https://www.blog.lavelo.es",
    "http://blog.lavelo.es",
    "http://www.blog.lavelo.es",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"📥 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} → {response.status_code} ({process_time:.2f}s)")
    
    return response

# Rutas absolutas para archivos estáticos
panel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'panel'))
falai_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'falai'))

# IMPORTANTE: Registrar routers ANTES de montar archivos estáticos
# (para que /api/* tenga prioridad sobre archivos estáticos)

# Incluir routers
from routers import posts, files, content, images, videos, validation, social

logger.info("🚀 Lavelo Blog API iniciada (FastAPI)")
logger.info(f"📁 Panel path: {panel_path}")
logger.info(f"📁 Falai path: {falai_path}")

app.include_router(posts.router)
app.include_router(files.router)
app.include_router(content.router)
app.include_router(images.router)
app.include_router(videos.router)
app.include_router(validation.router)
app.include_router(social.router)

logger.info("✅ Todos los routers registrados")

# Servir archivos estáticos del panel (CSS, JS, etc)
# Montar DESPUÉS de los routers para que /api/* tenga prioridad
if os.path.exists(panel_path):
    # Montar subdirectorios específicos
    css_path = os.path.join(panel_path, 'css')
    js_path = os.path.join(panel_path, 'js')
    
    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")
    
    # Montar panel completo para otros archivos
    app.mount("/panel", StaticFiles(directory=panel_path, html=True), name="panel")

if os.path.exists(falai_path):
    app.mount("/falai", StaticFiles(directory=falai_path, html=True), name="falai")

# Ruta raíz - Servir index.html del panel
@app.get("/")
async def root():
    return FileResponse(os.path.join(panel_path, "index.html"))

# Servir archivos HTML del panel (details.html, etc)
@app.get("/{filename}.html")
async def serve_html(filename: str):
    file_path = os.path.join(panel_path, f"{filename}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "framework": "FastAPI"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5002,
        reload=True,
        log_level="info"
    )
