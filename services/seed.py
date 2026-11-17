from database import SessionLocal, engine, Base
from models import Projeto, Fase, Tarefa, Responsavel, Documento

def init_db():
    # 1. Cria todas as tabelas fisicamente no banco de dados novo
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Se o banco estiver vazio, cadastra apenas os responsáveis básicos
        if db.query(Responsavel).count() == 0:
            resp1 = Responsavel(nome="Não atribuído")
            resp2 = Responsavel(nome="Administrador")
            db.add_all([resp1, resp2])
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
