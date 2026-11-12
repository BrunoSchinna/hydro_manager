import datetime
from models import Fase, Tarefa, Subtarefa

def aplicar_template_hydro(db, projeto_id, tipo_template):
    hoje = datetime.date.today()
    
    # ========================================================
    # TEMPLATE 1: PROJETO BÁSICO (Com tarefas e capítulos)
    # ========================================================
    if tipo_template == "Projeto Básico (Com tarefas e capítulos)":
        fase_pb = Fase(projeto_id=projeto_id, nome="Projeto Básico", ordem=1)
        db.add(fase_pb)
        db.flush()
        
        tarefas_pb = [
            "1 - HIDROLOGIA", "2 - TOPOGRAFIA", "3 - PLANILHAS DE CALCULO",
            "4 - ENERGETICOS", "5 - DESENHOS", "6 - TEXTOS",
            "7 - PLANILHAS TEXTO", "8 - ORCAMENTOS", "9 - FICHA RESUMO",
            "10 - CRONOGRAMA OBRAS", "11 - GEOLOGIA", "12 - DECLARAÇÃO DE RESPONSABILIDADE",
            "14 - SUMÁRIO EXECUTIVO", "15 - PROTOCOLO"
        ]
        
        subtarefas_textos = [
            "CAP 00 - ADENDO", "CAP 01 - APRESENTAÇÃO", 
            "CAP 02 - HISTÓRICO DE ESTUDOS E CARACTERISTICAS GERAIS",
            "CAP 03 - LEVANTAMENTOS COMPLEMENTARES", "CAP 04 - ESTUDOS HIDROLÓGICOS E MODELAGEM",
            "CAP 05 - ESTUDOS DE ALTERNATIVAS", "CAP 06 - DETALHAMENTO DO PROJETO",
            "CAP 07 - ESTUDOS AMBIENTAIS", "CAP 08 - INFRAESTRUTURA E LOGÍSTICA",
            "CAP 09 - PLANEJAMENTO DA CONSTRUÇÃO", "CAP 10 - ORÇAMENTO", "CAP 11 - FICHA TÉCNICA"
        ]
        
        for t_nome in tarefas_pb:
            nova_tarefa = Tarefa(
                fase_id=fase_pb.id, nome=t_nome, status="Não iniciada",
                prioridade="Alta" if t_nome in ["6 - TEXTOS", "15 - PROTOCOLO"] else "Média",
                responsavel="Não atribuído", data_inicio=hoje,
                data_termino=hoje + datetime.timedelta(days=15)
            )
            db.add(nova_tarefa)
            db.flush()
            
            if t_nome == "6 - TEXTOS":
                for sub_nome in subtarefas_textos:
                    db.add(Subtarefa(tarefa_id=nova_tarefa.id, nome=sub_nome, concluida=False))
        db.commit()

    # ========================================================
    # TEMPLATE 2: OUTORGA D'ÁGUA
    # ========================================================
    elif tipo_template == "Outorga D'água":
        fase_outorga = Fase(projeto_id=projeto_id, nome="Outorga D'água", ordem=1)
        db.add(fase_outorga)
        db.flush()
        
        tarefas_outorga = [
            "1 - REQUERIMENTO", "2 - CNPJ e CONTRATO SOCIAL", "3 - ART's",
            "4 - ESTUDO HIDROENERGETICO", "5 - DECLARAÇÃO LINDEIROS", "6 - RG RESPONSAVEL LEGAL",
            "7 - TAXA - OUTORGA", "8 - COMPROVANTE", "9 - CERTIDÃO DE DEBITOS AMBIENTAIS",
            "10 - ARRANJO GERAL", "11 - MAPA PROPRIETÁRIOS", "12 - MATRICULA"
        ]
        
        subtarefas_estudo = [
            "cap 03 - ESTUDOS HIDROMETEREOLÓGICOS E SEDIMENTOLÓGICOS",
            "cap 06 - ESTUDOS ENERGÉTICOS"
        ]
        
        for t_nome in tarefas_outorga:
            nova_tarefa = Tarefa(
                fase_id=fase_outorga.id, nome=t_nome, status="Não iniciada",
                prioridade="Alta" if t_nome == "4 - ESTUDO HIDROENERGETICO" else "Média",
                responsavel="Não atribuído", data_inicio=hoje,
                data_termino=hoje + datetime.timedelta(days=15)
            )
            db.add(nova_tarefa)
            db.flush()
            
            if t_nome == "4 - ESTUDO HIDROENERGETICO":
                for sub_nome in subtarefas_estudo:
                    db.add(Subtarefa(tarefa_id=nova_tarefa.id, nome=sub_nome, concluida=False))
        db.commit()
        
    # ========================================================
    # TEMPLATE 3: CRONOGRAMA PADRÃO COMPLETO
    # ========================================================
    elif tipo_template == "Cronograma Padrão Completo":
        fases_padrao = ["1. Estudos", "2. Projeto Básico", "3. Projeto Executivo", "4. Obras Civis"]
        for i, f_nome in enumerate(fases_padrao):
            db.add(Fase(projeto_id=projeto_id, nome=f_nome, ordem=i+1))
        db.commit()
