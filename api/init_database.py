#!/usr/bin/env python3
"""
Script para inicializar la base de datos MySQL
Crea las tablas necesarias
"""
from database import init_db, engine
from models import Base

def main():
    print("🔧 Inicializando base de datos MySQL...")
    print(f"📍 Conectando a: {engine.url}")
    
    try:
        # Crear todas las tablas
        init_db()
        
        # Verificar tablas creadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Base de datos inicializada correctamente")
        print(f"📊 Tablas creadas: {', '.join(tables)}")
        
    except Exception as e:
        print(f"\n❌ Error inicializando base de datos: {e}")
        raise

if __name__ == "__main__":
    main()
