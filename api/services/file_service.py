"""
Servicio de archivos local - Reemplaza Google Drive
Guarda archivos en sistema de archivos local (desarrollo) o servidor (producción)
"""
import os
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

# Path base de storage
STORAGE_PATH = os.getenv('STORAGE_PATH', os.path.join(os.path.dirname(__file__), '..', '..', 'storage'))

class FileService:
    """Servicio para gestionar archivos localmente (reemplaza Drive)"""
    
    def __init__(self):
        self.storage_path = Path(STORAGE_PATH)
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Crear carpeta storage si no existe"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Storage path: {self.storage_path}")
    
    def _get_post_path(self, codigo: str) -> Path:
        """Obtener path de un post"""
        return self.storage_path / 'posts' / codigo
    
    def _get_folder_path(self, codigo: str, folder: str) -> Path:
        """Obtener path de una carpeta dentro de un post"""
        return self._get_post_path(codigo) / folder
    
    def _get_file_path(self, codigo: str, folder: str, filename: str) -> Path:
        """Obtener path completo de un archivo"""
        return self._get_folder_path(codigo, folder) / filename
    
    def create_post_folders(self, codigo: str) -> Dict[str, str]:
        """
        Crea la estructura de carpetas para un post
        
        Returns:
            Dict con paths creados
        """
        post_path = self._get_post_path(codigo)
        
        folders = ['textos', 'imagenes', 'videos']
        created = {}
        
        for folder in folders:
            folder_path = post_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            created[folder] = str(folder_path)
        
        print(f"✅ Carpetas creadas para post {codigo}")
        return created
    
    def save_file(self, codigo: str, folder: str, filename: str, content: str) -> bool:
        """
        Guarda un archivo de texto
        
        Args:
            codigo: Código del post (ej: 20251029-1)
            folder: Carpeta (textos/imagenes/videos)
            filename: Nombre del archivo
            content: Contenido del archivo
        
        Returns:
            True si se guardó correctamente
        """
        try:
            file_path = self._get_file_path(codigo, folder, filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"💾 Guardado: {file_path}")
            return True
        except Exception as e:
            print(f"❌ Error guardando {filename}: {e}")
            return False
    
    def read_file(self, codigo: str, folder: str, filename: str) -> Optional[str]:
        """
        Lee un archivo de texto
        
        Returns:
            Contenido del archivo o None si no existe
        """
        try:
            file_path = self._get_file_path(codigo, folder, filename)
            
            if not file_path.exists():
                print(f"⚠️ Archivo no existe: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📖 Leído: {file_path} ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"❌ Error leyendo {filename}: {e}")
            return None
    
    def save_binary_file(self, codigo: str, folder: str, filename: str, data: bytes) -> bool:
        """
        Guarda un archivo binario (imágenes, videos)
        
        Args:
            data: Bytes del archivo
        """
        try:
            file_path = self._get_file_path(codigo, folder, filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(data)
            
            size_mb = len(data) / (1024 * 1024)
            print(f"💾 Guardado: {file_path} ({size_mb:.2f} MB)")
            return True
        except Exception as e:
            print(f"❌ Error guardando {filename}: {e}")
            return False
    
    def read_binary_file(self, codigo: str, folder: str, filename: str) -> Optional[bytes]:
        """
        Lee un archivo binario
        
        Returns:
            Bytes del archivo o None si no existe
        """
        try:
            file_path = self._get_file_path(codigo, folder, filename)
            
            if not file_path.exists():
                print(f"⚠️ Archivo no existe: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                data = f.read()
            
            size_mb = len(data) / (1024 * 1024)
            print(f"📖 Leído: {file_path} ({size_mb:.2f} MB)")
            return data
        except Exception as e:
            print(f"❌ Error leyendo {filename}: {e}")
            return None
    
    def file_exists(self, codigo: str, folder: str, filename: str) -> bool:
        """Verifica si un archivo existe"""
        file_path = self._get_file_path(codigo, folder, filename)
        return file_path.exists()
    
    def list_files(self, codigo: str, folder: str) -> List[str]:
        """
        Lista archivos en una carpeta
        
        Returns:
            Lista de nombres de archivos
        """
        try:
            folder_path = self._get_folder_path(codigo, folder)
            
            if not folder_path.exists():
                return []
            
            files = [f.name for f in folder_path.iterdir() if f.is_file()]
            return sorted(files)
        except Exception as e:
            print(f"❌ Error listando archivos: {e}")
            return []
    
    def delete_file(self, codigo: str, folder: str, filename: str) -> bool:
        """Elimina un archivo"""
        try:
            file_path = self._get_file_path(codigo, folder, filename)
            
            if file_path.exists():
                file_path.unlink()
                print(f"🗑️ Eliminado: {file_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error eliminando {filename}: {e}")
            return False
    
    def delete_post_folder(self, codigo: str) -> bool:
        """Elimina toda la carpeta de un post"""
        try:
            post_path = self._get_post_path(codigo)
            
            if post_path.exists():
                import shutil
                shutil.rmtree(post_path)
                print(f"🗑️ Carpeta eliminada: {post_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error eliminando carpeta: {e}")
            return False
    
    def get_file_url(self, codigo: str, folder: str, filename: str) -> str:
        """
        Obtiene URL para servir un archivo
        
        Returns:
            URL relativa para el endpoint de FastAPI
        """
        return f"/api/files/{codigo}/{folder}/{filename}"
    
    def get_storage_info(self) -> Dict:
        """Obtiene información del storage"""
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.storage_path):
                for file in files:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                'path': str(self.storage_path),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'exists': self.storage_path.exists()
            }
        except Exception as e:
            return {
                'path': str(self.storage_path),
                'error': str(e)
            }

# Instancia global
file_service = FileService()
