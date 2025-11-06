#!/usr/bin/env python3
"""
Script para crear tablas en la base de datos
"""
from database import engine
from db_models import Base

print("🔧 Creando tablas en base de datos...")

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

print("✅ Tablas creadas exitosamente")
print("\nTablas disponibles:")
for table in Base.metadata.tables.keys():
    print(f"  - {table}")
