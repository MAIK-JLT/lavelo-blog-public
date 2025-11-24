"""
Configuración de base de datos con SQLAlchemy
Usa SQLite en local y MySQL en producción
"""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
import os

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# Detectar entorno
IS_PRODUCTION = os.getenv('ENVIRONMENT', 'development') == 'production'

if IS_PRODUCTION:
    # Producción: MySQL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no está configurada en .env")
else:
    # Local: SQLite
    db_path = os.path.join(os.path.dirname(__file__), 'lavelo_blog.db')
    DATABASE_URL = f'sqlite:///{db_path}'
    print(f" Usando SQLite local: {db_path}")

# Crear engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    pool_recycle=3600,   # Recicla conexiones cada hora
    echo=False,          # No mostrar SQL queries (cambiar a True para debug)
    connect_args={
        # Mitigar locks en SQLite local
        "timeout": 30,
        "check_same_thread": False
    } if DATABASE_URL.startswith("sqlite") else {}
)

# Activar WAL, busy_timeout y synchronous en SQLite local
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    try:
        # Solo aplica a SQLite
        if getattr(dbapi_conn, "execute", None):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=120000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    except Exception:
        # No romper en otros motores
        pass

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
    from db_models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas en MySQL")
