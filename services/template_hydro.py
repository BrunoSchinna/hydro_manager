import datetime
from models import Fase, Tarefa, Subtarefa

def aplicar_template_hydro(db, projeto_id, tipo_template):
    hoje = datetime.date.today()
    
    # ========================================================
    # TEMPLATE 1: PROJETO BÁSICO (Com tarefas e subtarefas)
    # ========================================================
    if tipo_template == "Projeto Básico (Com tarefas e capítulos)":
        
        # 1. Cria a Fase Principal
        fase_pb = Fase(projeto_id=projeto_id, nome="Projeto Básico", ordem=1)
        db.add(fase_pb)
        db.flush() # Registra rápido no banco para gerar o ID da fase
        
        # 2. Lista de Tarefas do Projeto Básico
        tarefas_pb = [
            "1 - HIDROLOGIA", "2 - TOPOGRAFIA", "3 - PLANILHAS DE CALCULO",
            "4 - ENERGETICOS", "5 - DESENHOS", "6 - TEXTOS",
            "7 - PLANILHAS TEXTO", "8 - ORCAMENTOS", "9 - FICHA RESUMO",
            "10 - CRONOGRAMA OBRAS", "11 - GEOLOGIA", "12 - DECLARAÇÃO DE RESPONSABILIDADE",
            "14 - SUMÁRIO EXECUTIVO", "15 - PROTOCOLO"
        ]
        
        # 3. Lista de Subtarefas exclusivas da tarefa "6 - TEXTOS"
        subtarefas_textos = [
            "CAP 00 - ADENDO", "CAP 01 - APRESENTAÇÃO", 
            "CAP 02 - HISTÓRICO DE ESTUDOS E CARACTERISTICAS GERAIS",
            "CAP 03 - LEVANTAMENTOS COMPLEMENTARES", "CAP 04 - ESTUDOS HIDROLÓGICOS E MODELAGEM",
            "CAP 05 - ESTUDOS DE ALTERNATIVAS", "CAP 06 - DETALHAMENTO DO PROJETO",
            "CAP 07 - ESTUDOS AMBIENTAIS", "CAP 08 - INFRAESTRUTURA E LOGÍSTICA",
            "CAP 09 - PLANEJAMENTO DA CONSTRUÇÃO", "CAP 10 - ORÇAMENTO", "CAP 11 - FICHA TÉCNICA"
        ]
        
        # 4. Cadastra tudo de uma vez no banco
        for t_nome in tarefas_pb:
            nova_tarefa = Tarefa(
                fase_id=fase_pb.id,
                nome=t_nome,
                status="Não iniciada",
                prioridade="Alta" if t_nome in ["6 - TEXTOS", "15 - PROTOCOLO"] else "Média",
                responsavel="Não atribuído",
                data_inicio=hoje,
                data_termino=hoje + datetime.timedelta(days=15) # Prazo inicial padrão estipulado em 15 dias
            )
            db.add(nova_tarefa)
            db.flush()
            
            # Quando chegar na tarefa 6, o sistema varre o checklist de capítulos
            if t_nome == "6 - TEXTOS":
                for sub_nome in subtarefas_textos:
                    db.add(Subtarefa(tarefa_id=nova_tarefa.id, nome=sub_nome, concluida=False))
                    
        db.commit()
        
    # ========================================================
    # TEMPLATE 2: CRONOGRAMA PADRÃO COMPLETO (Sua versão antiga)
    # ========================================================
    elif tipo_template == "Cronograma Padrão Completo":
        # Se você já tinha um código aqui antes que gerava as 14 fases, você pode colá-lo aqui dentro.
        # Por enquanto deixei um modelo básico para ele não dar erro.
        fases_padrao = ["1. Estudos", "2. Projeto Básico", "3. Projeto Executivo", "4. Obras Civis"]
        for i, f_nome in enumerate(fases_padrao):
            f = Fase(projeto_id=projeto_id, nome=f_nome, ordem=i+1)
            db.add(f)
        db.commit()
