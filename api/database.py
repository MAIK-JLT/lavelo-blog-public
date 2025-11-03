"""
Conexión a base de datos MySQL
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()  # Busca .env en el directorio actual (/api)

# Obtener URL de base de datos
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurada en .env")

# Crear engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    pool_recycle=3600,   # Recicla conexiones cada hora
    echo=False           # No mostrar SQL queries (cambiar a True para debug)
)

# Crear session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Session con scope (thread-safe)
db_session = scoped_session(SessionLocal)

def get_db():
    """
    Dependency para obtener sesión de base de datos
    Uso: db = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Inicializa la base de datos (crea tablas)
    """
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas en MySQL")
