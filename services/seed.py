import datetime
from database import engine, SessionLocal, Base
from models import Responsavel, Projeto, Fase, Tarefa

def init_db():
    # Cria todas as tabelas no banco de dados
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Verifica se já existem projetos. Se não, cria a nossa PCH de exemplo.
    if db.query(Projeto).count() == 0:
        # 1. Cria um Responsável de exemplo
        eng = Responsavel(nome="Eng. João Silva", email="joao@hydromanager.com")
        db.add(eng)
        db.commit()
        db.refresh(eng)
        
        # 2. Cria o Projeto PCH
        projeto = Projeto(
            nome="PCH Rio Claro",
            tipo="PCH",
            rio="Rio Claro",
            municipio_uf="Xanxerê/SC",
            potencia_mw=30.0,
            responsavel_id=eng.id,
            data_inicio=datetime.date.today(),
            data_termino_prevista=datetime.date.today() + datetime.timedelta(days=365),
            status="Em andamento",
            descricao="Projeto fictício de demonstração gerado automaticamente."
        )
        db.add(projeto)
        db.commit()
        db.refresh(projeto)
        
        # 3. Cria uma Fase básica só para não ficar vazio (vamos aprofundar isso na Etapa 5)
        fase1 = Fase(projeto_id=projeto.id, nome="1. Estudos de Viabilidade", ordem=1, cor="#e67e22")
        db.add(fase1)
        db.commit()
        
    db.close()