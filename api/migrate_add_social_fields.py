#!/usr/bin/env python3
"""
Migración: Añadir page_id e instagram_account_id a social_tokens
"""
import os
import sys
from dotenv import load_dotenv

# Cargar .env (producción primero, luego fallback local)
default_env = os.path.join(os.path.dirname(__file__), '..', '.env')
env_file = os.getenv('ENV_FILE', os.getenv('LAVELO_ENV_FILE', '/var/www/vhosts/blog.lavelo.es/private/.env'))
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=default_env)

# Importar database
from database import engine
from sqlalchemy import text

def migrate():
    """Ejecutar migración"""
    
    # Detectar si es SQLite o MySQL
    is_sqlite = 'sqlite' in str(engine.url)
    
    if is_sqlite:
        print("📦 Detectado SQLite")
        sql = """
        ALTER TABLE social_tokens ADD COLUMN page_id VARCHAR(100);
        ALTER TABLE social_tokens ADD COLUMN instagram_account_id VARCHAR(100);
        """
    else:
        print("🐬 Detectado MySQL")
        sql = """
        ALTER TABLE social_tokens 
        ADD COLUMN page_id VARCHAR(100) AFTER username,
        ADD COLUMN instagram_account_id VARCHAR(100) AFTER page_id;
        """
    
    try:
        with engine.connect() as conn:
            # SQLite requiere ejecutar cada ALTER TABLE por separado
            if is_sqlite:
                conn.execute(text("ALTER TABLE social_tokens ADD COLUMN page_id VARCHAR(100)"))
                print("✅ Columna page_id añadida")
                conn.execute(text("ALTER TABLE social_tokens ADD COLUMN instagram_account_id VARCHAR(100)"))
                print("✅ Columna instagram_account_id añadida")
            else:
                conn.execute(text(sql))
                print("✅ Columnas añadidas")
            
            conn.commit()
        
        print("\n🎉 Migración completada exitosamente")
        
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print("⚠️  Las columnas ya existen, migración no necesaria")
        else:
            print(f"❌ Error en migración: {e}")
            raise

if __name__ == '__main__':
    migrate()
