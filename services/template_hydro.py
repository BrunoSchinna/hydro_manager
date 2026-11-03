import datetime
from sqlalchemy.orm import Session
from models import Fase, Tarefa, Dependencia

def aplicar_template_hydro(db: Session, projeto_id: int):
    # 1. Definir as fases padrão do ciclo de vida de PCH/UHE
    fases_nomes = [
        "1. Estudos de Inventário e Viabilidade",
        "2. Projeto Básico e ANEEL",
        "3. Licenciamento Ambiental (LP/LI/LO) e PBA",
        "4. Fundiário (Desapropriação e Servidões)",
        "5. Projeto Executivo",
        "6. Canteiro de Obras e Acessos",
        "7. Desvio do Rio e Ensecadeiras",
        "8. Barragem, Vertedouro e Adução",
        "9. Casa de Força (Civil)",
        "10. Equipamentos Eletromecânicos",
        "11. Linha de Transmissão e SE",
        "12. Montagem, Comissionamento e Testes",
        "13. Enchimento do Reservatório",
        "14. Operação Comercial (COD)"
    ]
    
    fases_dict = {}
    for i, nome in enumerate(fases_nomes, 1):
        nova_fase = Fase(projeto_id=projeto_id, nome=nome, ordem=i)
        db.add(nova_fase)
        db.flush() # Envia pro banco rapidinho para gerar o ID sem finalizar a transação
        fases_dict[i] = nova_fase

    # 2. Criar algumas tarefas iniciais de exemplo conectadas às fases
    hoje = datetime.date.today()
    
    t_topo = Tarefa(fase_id=fases_dict[1].id, nome="Levantamento Topográfico Planialtimétrico", 
                    data_inicio=hoje, data_termino=hoje + datetime.timedelta(days=30))
    t_geo = Tarefa(fase_id=fases_dict[1].id, nome="Investigações Geotécnicas (Sondagens)", 
                   data_inicio=hoje + datetime.timedelta(days=10), data_termino=hoje + datetime.timedelta(days=40))
    t_eia = Tarefa(fase_id=fases_dict[3].id, nome="Elaboração do EIA/RIMA", 
                   data_inicio=hoje + datetime.timedelta(days=45), data_termino=hoje + datetime.timedelta(days=180))
    t_cod = Tarefa(fase_id=fases_dict[14].id, nome="Declaração de Operação Comercial (COD)", 
                   data_inicio=hoje + datetime.timedelta(days=700), data_termino=hoje + datetime.timedelta(days=700), is_marco=True)
    
    db.add_all([t_topo, t_geo, t_eia, t_cod])
    db.flush()

    # 3. Criar uma dependência de exemplo (O EIA/RIMA precisa da topografia base)
    dep1 = Dependencia(tarefa_predecessora_id=t_topo.id, tarefa_sucessora_id=t_eia.id)
    db.add(dep1)
    
    db.commit()