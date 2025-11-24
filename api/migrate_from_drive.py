"""
Script para migrar posts de Google Drive a BD local + Storage
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

default_env = os.path.join(os.path.dirname(__file__), '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

sys.path.append(os.path.dirname(__file__))
from database import SessionLocal
from db_models import Post
from services.file_service import file_service

def migrate_posts_from_drive():
    """
    Lee posts de Google Drive y los importa a BD local
    """
    print("🔄 Migrando posts desde Google Drive...")
    
    db = SessionLocal()
    
    try:
        # Listar posts desde Drive
        posts_data = file_service.list_posts_from_drive()
        
        if not posts_data:
            print("❌ No se encontraron posts en Drive")
            return
        
        print(f"📦 Encontrados {len(posts_data)} posts en Drive")
        
        for post_data in posts_data:
            codigo = post_data.get('codigo')
            
            # Verificar si ya existe en BD
            existing = db.query(Post).filter(Post.codigo == codigo).first()
            if existing:
                print(f"⏭️  {codigo} ya existe en BD, saltando...")
                continue
            
            # Crear post en BD
            post = Post(
                codigo=codigo,
                titulo=post_data.get('titulo', 'Sin título'),
                categoria=post_data.get('categoria', 'General'),
                estado=post_data.get('estado', 'DRAFT'),
                fecha_programada=post_data.get('fecha_programada'),
                hora_programada=post_data.get('hora_programada'),
                redes_seleccionadas=post_data.get('redes_seleccionadas', '{}'),
                created_at=datetime.now()
            )
            
            db.add(post)
            print(f"✅ {codigo} importado a BD")
        
        db.commit()
        print(f"🎉 Migración completada: {len(posts_data)} posts")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        db.rollback()
    finally:
        db.close()

def download_files_from_drive():
    """
    Descarga archivos de Drive a storage local
    """
    print("📥 Descargando archivos desde Drive...")
    
    # TODO: Implementar descarga de archivos
    # Por ahora, los archivos se quedan en Drive
    # El panel puede leerlos directamente con file_service
    
    print("⚠️  Archivos permanecen en Drive (acceso directo)")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrar posts de Drive a BD')
    parser.add_argument('--download-files', action='store_true', 
                       help='Descargar archivos a storage local')
    
    args = parser.parse_args()
    
    migrate_posts_from_drive()
    
    if args.download_files:
        download_files_from_drive()
