#!/usr/bin/env python3
"""
Script de Migración: Google Drive + Sheets → BD Local + Storage

Migra todos los posts desde:
- Google Sheets (metadata) → MySQL/SQLite
- Google Drive (archivos) → /storage/posts/

Uso:
    python3 migrate_drive_to_local.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import io

# Cargar .env
load_dotenv()

# Importar servicios
sys.path.append(os.path.dirname(__file__))
from database import SessionLocal
from db_models import Post
from sheets_service import SheetsService
from googleapiclient.http import MediaIoBaseDownload

class DriveToLocalMigrator:
    """Migrador de Google Drive/Sheets a BD local + Storage"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.storage_path = Path(os.getenv('STORAGE_PATH', '../storage'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Usar servicio existente de Google
        print("🔄 Conectando con Google Sheets/Drive...")
        self.google_service = SheetsService()
        
        if not self.google_service.service or not self.google_service.drive_service:
            print("❌ No se pudo conectar con Google. Verifica config/token.json")
            print("   Ejecuta primero el panel web para autenticarte")
            self.sheets_service = None
            self.drive_service = None
        else:
            self.sheets_service = self.google_service.service
            self.drive_service = self.google_service.drive_service
            print("✅ Conectado con Google Sheets/Drive")
    
    def migrate_from_sheets(self, spreadsheet_id: str):
        """
        Migra posts desde Google Sheets a BD
        
        Args:
            spreadsheet_id: ID del spreadsheet (desde URL)
        """
        if not self.sheets_service:
            print("❌ Google Sheets no disponible")
            return
        
        print(f"📊 Leyendo posts desde Google Sheets...")
        
        try:
            # Leer datos del sheet
            range_name = 'Posts!A2:Z1000'  # Ajustar según tu sheet
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            
            if not rows:
                print("❌ No se encontraron datos en el sheet")
                return
            
            print(f"📦 Encontradas {len(rows)} filas")
            
            # Mapear columnas (ajustar según tu sheet)
            # Ejemplo: A=codigo, B=titulo, C=categoria, D=estado, etc.
            for i, row in enumerate(rows, start=2):
                try:
                    if len(row) < 4:
                        continue
                    
                    codigo = row[0] if len(row) > 0 else None
                    titulo = row[1] if len(row) > 1 else 'Sin título'
                    categoria = row[2] if len(row) > 2 else 'General'
                    estado = row[3] if len(row) > 3 else 'DRAFT'
                    fecha_prog = row[4] if len(row) > 4 else None
                    hora_prog = row[5] if len(row) > 5 else None
                    
                    if not codigo:
                        continue
                    
                    # Verificar si ya existe
                    existing = self.db.query(Post).filter(Post.codigo == codigo).first()
                    if existing:
                        print(f"⏭️  {codigo} ya existe, saltando...")
                        continue
                    
                    # Parsear fecha
                    fecha_obj = None
                    if fecha_prog:
                        try:
                            fecha_obj = datetime.strptime(fecha_prog, '%Y-%m-%d').date()
                        except:
                            try:
                                fecha_obj = datetime.strptime(fecha_prog, '%d/%m/%Y').date()
                            except:
                                pass
                    
                    # Crear post
                    post = Post(
                        codigo=codigo,
                        titulo=titulo,
                        categoria=categoria,
                        estado=estado,
                        fecha_programada=fecha_obj,
                        hora_programada=hora_prog,
                        created_at=datetime.now()
                    )
                    
                    self.db.add(post)
                    print(f"✅ {codigo}: {titulo}")
                    
                except Exception as e:
                    print(f"❌ Error en fila {i}: {e}")
                    continue
            
            self.db.commit()
            print(f"🎉 Migración de Sheets completada")
            
        except Exception as e:
            print(f"❌ Error leyendo Sheets: {e}")
            self.db.rollback()
    
    def migrate_from_drive(self, folder_id: str):
        """
        Migra archivos desde Google Drive a storage local
        
        Args:
            folder_id: ID de la carpeta raíz en Drive
        """
        if not self.drive_service:
            print("❌ Google Drive no disponible")
            return
        
        print(f"📁 Descargando archivos desde Google Drive...")
        
        try:
            # Listar carpetas de posts (ej: 20251105-1, 20251105-2)
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            post_folders = results.get('files', [])
            
            print(f"📦 Encontradas {len(post_folders)} carpetas de posts")
            
            for post_folder in post_folders:
                codigo = post_folder['name']
                folder_id = post_folder['id']
                
                print(f"\n📥 Descargando {codigo}...")
                
                # Crear carpeta local
                post_path = self.storage_path / 'posts' / codigo
                post_path.mkdir(parents=True, exist_ok=True)
                
                # Descargar subcarpetas (textos, imagenes, videos)
                self._download_folder_contents(folder_id, post_path)
            
            print(f"\n🎉 Migración de Drive completada")
            
        except Exception as e:
            print(f"❌ Error descargando de Drive: {e}")
    
    def _download_folder_contents(self, folder_id: str, local_path: Path):
        """Descarga recursivamente contenido de una carpeta"""
        try:
            # Listar contenido
            query = f"'{folder_id}' in parents"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType)"
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                item_name = item['name']
                item_id = item['id']
                mime_type = item['mimeType']
                
                if mime_type == 'application/vnd.google-apps.folder':
                    # Es una carpeta, crear localmente y descargar contenido
                    subfolder_path = local_path / item_name
                    subfolder_path.mkdir(exist_ok=True)
                    self._download_folder_contents(item_id, subfolder_path)
                else:
                    # Es un archivo, descargar
                    file_path = local_path / item_name
                    self._download_file(item_id, file_path)
                    print(f"  ✅ {file_path.relative_to(self.storage_path)}")
        
        except Exception as e:
            print(f"❌ Error descargando carpeta: {e}")
    
    def _download_file(self, file_id: str, local_path: Path):
        """Descarga un archivo de Drive"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            
            with io.FileIO(str(local_path), 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
        
        except Exception as e:
            print(f"❌ Error descargando archivo: {e}")
    
    def close(self):
        """Cerrar conexión a BD"""
        self.db.close()

def main():
    """Función principal"""
    print("=" * 60)
    print("🔄 MIGRACIÓN: Google Drive + Sheets → BD Local + Storage")
    print("=" * 60)
    
    # IDs de Google (obtener de URLs)
    SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID', '1f88LjU0gcBaYm_pqC9c5R29slGLHO6YASesZ8trouug')
    DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')  # ID de carpeta "Posts" en Drive
    
    migrator = DriveToLocalMigrator()
    
    try:
        # Paso 1: Migrar metadata desde Sheets
        print("\n" + "=" * 60)
        print("PASO 1: Migrar metadata desde Google Sheets")
        print("=" * 60)
        
        if SPREADSHEET_ID:
            migrator.migrate_from_sheets(SPREADSHEET_ID)
        else:
            print("⚠️  GOOGLE_SHEET_ID no configurado en .env")
        
        # Paso 2: Migrar archivos desde Drive
        print("\n" + "=" * 60)
        print("PASO 2: Migrar archivos desde Google Drive")
        print("=" * 60)
        
        if DRIVE_FOLDER_ID:
            migrator.migrate_from_drive(DRIVE_FOLDER_ID)
        else:
            print("⚠️  GOOGLE_DRIVE_FOLDER_ID no configurado en .env")
            print("   Obtén el ID desde la URL de la carpeta en Drive")
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 60)
        
    finally:
        migrator.close()

if __name__ == '__main__':
    main()
