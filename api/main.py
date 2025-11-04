from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="Lavelo Blog API",
    description="API para gestión automatizada de contenido de triatlón",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS - Permitir todas las peticiones (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas absolutas para archivos estáticos
panel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'panel'))
falai_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'falai'))

# IMPORTANTE: Registrar routers ANTES de montar archivos estáticos
# (para que /api/* tenga prioridad sobre archivos estáticos)

# Incluir routers
from routers import posts, files, content, images, videos, validation, social
app.include_router(posts.router)
app.include_router(files.router)
app.include_router(content.router)
app.include_router(images.router)
app.include_router(videos.router)
app.include_router(validation.router)
app.include_router(social.router)

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
        port=5001,
        reload=True,
        log_level="info"
    )
