import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Puxa a URL e remove aspas ou espaços vazios
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./hydro_manager.db")
DATABASE_URL = DATABASE_URL.strip().strip('"').strip("'")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./hydro_manager.db"

# 2. Força o SQLAlchemy a usar o tradutor psycopg2 (resolve o erro de importação)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# 3. Conexão
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
