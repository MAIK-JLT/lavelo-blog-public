"""
Servicio para gestionar posts
Usado por: MCP Server, Panel Web, API REST
"""
from typing import List, Optional, Dict
from datetime import datetime
import sys
import os

# Agregar path para importar db_service
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import db_service
from services.file_service import file_service

class PostService:
    """Servicio centralizado para operaciones con posts"""
    
    def __init__(self):
        self.file_service = file_service
    
    async def list_posts(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Lista todos los posts desde MySQL
        
        Usado por:
        - Panel Web: Selector de posts
        - MCP: list_posts()
        - API: GET /api/posts
        """
        posts = db_service.get_all_posts()
        
        if limit:
            posts = posts[:limit]
        
        return posts
    
    async def get_post(self, codigo: str) -> Optional[Dict]:
        """
        Obtiene un post por código
        
        Usado por:
        - Panel Web: Cargar detalles
        - MCP: get_post()
        - API: GET /api/posts/{codigo}
        """
        return db_service.get_post_by_codigo(codigo)
    
    async def create_post(
        self,
        titulo: str,
        categoria: str,
        idea: Optional[str] = None,
        fecha_programada: Optional[str] = None,
        hora_programada: Optional[str] = None
    ) -> Dict:
        """
        Crea un nuevo post con carpeta en Drive
        
        Usado por:
        - MCP: create_post()
        - Panel: Botón "Crear Post"
        - API: POST /api/posts
        """
        # Generar código YYYYMMDD-ref
        fecha_str = datetime.now().strftime('%Y%m%d')
        posts_hoy = [p for p in db_service.get_all_posts() if p['codigo'].startswith(fecha_str)]
        numero = len(posts_hoy) + 1
        codigo = f"{fecha_str}-{numero}"
        
        # Crear carpetas locales
        self.file_service.create_post_folders(codigo)
        
        # Crear post en MySQL
        post_data = {
            'codigo': codigo,
            'titulo': titulo,
            'categoria': categoria,
            'idea': idea,
            'estado': 'BASE_TEXT_AWAITING',  # Estado inicial correcto
            'drive_folder_id': None,  # Ya no usamos Drive
            'fecha_programada': fecha_programada,
            'hora_programada': hora_programada
        }
        
        success = db_service.create_post(post_data)
        
        if not success:
            raise Exception(f"Error creando post {codigo}")
        
        # Crear base.txt inicial
        content = f"# {titulo}\n\n{idea or ''}"
        self.file_service.save_file(codigo, 'textos', f"{codigo}_base.txt", content)
        
        # Marcar checkbox de base.txt
        db_service.update_post(codigo, {'base_txt': True})
        
        return {
            'success': True,
            'codigo': codigo,
            'post': db_service.get_post_by_codigo(codigo),
            'message': f"✅ Post {codigo} creado exitosamente"
        }
    
    async def update_post(self, codigo: str, updates: Dict) -> Dict:
        """
        Actualiza un post
        
        Usado por:
        - Panel Web: Guardar cambios
        - API: PATCH /api/posts/{codigo}
        """
        success = db_service.update_post(codigo, updates)
        
        if not success:
            raise Exception(f"Error actualizando post {codigo}")
        
        return {
            'success': True,
            'post': db_service.get_post_by_codigo(codigo),
            'message': f"✅ Post {codigo} actualizado"
        }
    
    async def delete_post(self, codigo: str) -> Dict:
        """
        Elimina un post
        
        Usado por:
        - Panel Web: Botón "Eliminar"
        - API: DELETE /api/posts/{codigo}
        """
        success = db_service.delete_post(codigo)
        
        if not success:
            raise Exception(f"Error eliminando post {codigo}")
        
        return {
            'success': True,
            'message': f"✅ Post {codigo} eliminado"
        }
    
    async def init_post_folders(self, codigo: str) -> Dict:
        """
        Inicializa carpetas locales para un post
        
        Usado por:
        - MCP: init_post_folders()
        - Panel: Botón "Inicializar Carpetas"
        - API: POST /api/posts/{codigo}/init-folders
        """
        post = db_service.get_post_by_codigo(codigo)
        
        if not post:
            raise Exception(f"Post {codigo} no encontrado")
        
        # Crear carpetas locales
        created_paths = self.file_service.create_post_folders(codigo)
        created = list(created_paths.keys())
        
        return {
            'success': True,
            'created': created,
            'paths': created_paths,
            'message': f"✅ Carpetas inicializadas: {', '.join(created)}"
        }
