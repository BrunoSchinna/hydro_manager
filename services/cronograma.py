from sqlalchemy.orm import Session
import datetime
from models import Tarefa, Dependencia

def recalcular_datas_sucessoras(db: Session, tarefa_id: int):
    """
    Função recursiva para atualizar as datas das tarefas sucessoras.
    Se a Tarefa A (predecessora) terminar dia 10, a Tarefa B (sucessora Fim-Início)
    não pode começar antes do dia 10.
    """
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa or not tarefa.data_termino: 
        return
    
    # Busca dependências onde a tarefa atual é a predecessora
    deps = db.query(Dependencia).filter(Dependencia.tarefa_predecessora_id == tarefa.id).all()
    
    for dep in deps:
        if dep.tipo == "Fim-Início":
            sucessora = dep.sucessora
            # Se a sucessora começa antes da predecessora terminar, empurramos ela para frente
            if sucessora.data_inicio < tarefa.data_termino:
                # Calcula quantos dias a sucessora durava para manter a duração original
                duracao = (sucessora.data_termino - sucessora.data_inicio).days
                
                sucessora.data_inicio = tarefa.data_termino
                sucessora.data_termino = sucessora.data_inicio + datetime.timedelta(days=duracao)
                
                db.commit()
                # Chama recursivamente caso essa sucessora também tenha suas próprias sucessoras
                recalcular_datas_sucessoras(db, sucessora.id)