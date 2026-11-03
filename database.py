from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuração do SQLite local
DATABASE_URL = "sqlite:///hydro_manager.db"

# Engine do banco de dados com suporte a foreign keys no SQLite
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Habilitar pragma foreign_keys para SQLite
from sqlalchemy import event
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Gera uma sessão do banco de dados para ser usada nas operações."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
