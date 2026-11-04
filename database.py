import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Busca a URL do banco nas variáveis de ambiente do Render. 
# Se não encontrar (rodando no seu PC local), usa o arquivo SQLite padrão.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./hydro_manager.db")

# 2. Correção de compatibilidade: o SQLAlchemy exige 'postgresql://' em vez do antigo 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. O SQLite exige um parâmetro especial para evitar erros de thread que o Postgres não precisa
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
