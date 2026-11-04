import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Projeto, Fase, Tarefa, Responsavel, Subtarefa, Historico
import datetime

st.set_page_config(page_title="Painel de Tarefas", page_icon="📋", layout="wide")

# --- 0. TRAVA DE SEGURANÇA (AUTENTICAÇÃO) ---
if not st.session_state.get("autenticado", False):
    st.warning("🔒 Acesso restrito. Faça login na página inicial primeiro.")
    st.page_link("app.py", label="⬅️ Ir para a página de Login")
    st.stop()

# Barra lateral
with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state.get('usuario_nome', '')}**")
    st.page_link("app.py", label="🏠 Início / Projetos")
    st.divider()

if 'projeto_ativo_id' not in st.session_state:
    st.warning("Nenhum projeto selecionado. Volte para a página inicial e escolha um projeto.")
    st.page_link("app.py", label="⬅️ Voltar para a Página Inicial")
    st.stop()

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

db = get_db()
projeto_id = st.session_state['projeto_ativo_id']
projeto = db.query(Projeto).filter(Projeto.id == projeto_id).first()

# --- FUNÇÕES ESPIÃS (AUDITORIA E MATEMÁTICA) ---
def registrar_acao(db, acao, detalhes):
    """Grava silenciosamente tudo o que os usuários fazem no sistema."""
    usuario = st.session_state.get('usuario_nome', 'Sistema')
    log = Historico(usuario=usuario, acao=acao, detalhes=f"[Projeto: {projeto.nome}] {detalhes}")
    db.add(log)

def atualizar_progresso_subtarefas(db, tarefa_id):
    """Calcula automaticamente a % da tarefa mãe baseado nos checks das subtarefas."""
    subtarefas = db.query(Subtarefa).filter(Subtarefa.tarefa_id == tarefa_id).all()
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    
    if subtarefas and tarefa:
        total = len(subtarefas)
        concluidas = sum(1 for s in subtarefas if s.concluida)
        novo_pct = (concluidas / total) * 100.0
        
        tarefa.percentual_concluido = novo_pct
        if novo_pct == 100.0:
            tarefa.status = "Concluída"
        elif novo_pct > 0 and tarefa.status == "Não iniciada":
            tarefa.status = "Em andamento"

st.title(f"📋 Painel de Tarefas: {projeto.nome}")
st.page_link("app.py", label="⬅️ Voltar para Projetos")
st.divider()

# --- 1. FILTROS ---
st.subheader("Filtros")
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
busca = col_f1.text_input("🔍 Buscar por nome da tarefa")
filtro_status = col_f2.selectbox("Status", ["Todos", "Não iniciada", "Em andamento", "Travada", "Concluída"])
filtro_prio = col_f3.selectbox("Prioridade", ["Todas", "Baixa", "Média", "Alta", "Crítica"])

fases_db = db.query(Fase).filter(Fase.projeto_id == projeto_id).order_by(Fase.ordem).all()
opcoes_fase = ["Todas"] + [f.nome for f in fases_db]
filtro_fase = col_f4.selectbox("Fase", opcoes_fase)

query = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == projeto_id)
if busca: query = query.filter(Tarefa.nome.ilike(f"%{busca}%"))
if filtro_status != "Todos": query = query.filter(Tarefa.status == filtro_status)
if filtro_prio != "Todas": query = query.filter(Tarefa.prioridade == filtro_prio)
if filtro_fase != "Todas": query = query.filter(Fase.nome == filtro_fase)

tarefas = query.order_by(Fase.ordem, Tarefa.data_inicio).all()

# --- 2. ABAS DE VISUALIZAÇÃO ---
aba_tabela, aba_kanban, aba_subtarefas = st.tabs(["📝 Tabela de Tarefas", "🗂️ Kanban (Quadro)", "✅ Subtarefas (Checklist)"])

with aba_tabela:
    st.markdown("### Edição Rápida")
    st.write("Edite as informações na tabela e clique em **Salvar Alterações**.")
    
    if not tarefas:
        st.info("Nenhuma tarefa encontrada.")
    else:
        dados = []
        for t in tarefas:
            # Se a tarefa tiver subtarefas cadastradas, travamos a edição manual marcando com um aviso no nome
            tem_sub = db.query(Subtarefa).filter(Subtarefa.tarefa_id == t.id).count() > 0
            
            dados.append({
                "ID": t.id,
                "Fase": t.fase.nome,
                "Tarefa": t.nome + (" 🔒 (Automático)" if tem_sub else ""),
                "Status": t.status,
                "Prioridade": t.prioridade,
                "Início": t.data_inicio,
                "Término": t.data_termino,
                "% Concluído": float(t.percentual_concluido or 0.0),
                "Marco?": t.is_marco,
                "Possui Subtarefas": tem_sub
            })
        
        df = pd.DataFrame(dados)
        
        df_editado = st.data_editor(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", disabled=True),
                "Fase": st.column_config.TextColumn("Fase", disabled=True),
                "Tarefa": st.column_config.TextColumn("Tarefa", disabled=True), # Bloqueado para não apagar o cadeado sem querer
                "Status": st.column_config.SelectboxColumn("Status", options=["Não iniciada", "Em andamento", "Travada", "Concluída"]),
                "Prioridade": st.column_config.SelectboxColumn("Prioridade", options=["Baixa", "Média", "Alta", "Crítica"]),
                "Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Término": st.column_config.DateColumn("Término", format="DD/MM/YYYY"),
                "% Concluído": st.column_config.NumberColumn("% Concluído", min_value=0.0, max_value=100.0, format="%d%%", step=5.0),
                "Possui Subtarefas": None # Esconde essa coluna técnica
            },
            hide_index=True,
            use_container_width=True,
            key="editor_tarefas"
        )
        
        if st.button("💾 Salvar Alterações da Tabela", type="primary"):
            for index, row in df_editado.iterrows():
                tarefa_db = db.query(Tarefa).filter(Tarefa.id == row["ID"]).first()
                if tarefa_db:
                    tarefa_db.status = row["Status"]
                    tarefa_db.prioridade = row["Prioridade"]
                    tarefa_db.data_inicio = row["Início"]
                    tarefa_db.data_termino = row["Término"]
                    tarefa_db.is_marco = row["Marco?"]
                    
                    # Regra de salvamento: se tiver subtarefa, ignora a digitação manual. 
                    if row["Possui Subtarefas"]:
                        atualizar_progresso_subtarefas(db, tarefa_db.id)
                    else:
                        if row["Status"] == "Concluída":
                            tarefa_db.percentual_concluido = 100.0
                        else:
                            tarefa_db.percentual_concluido = row["% Concluído"]
                            
            registrar_acao(db, "Edição em Lote", "Salvou modificações na Tabela de Tarefas.")
            db.commit()
            st.success("Alterações salvas com sucesso!")
            st.rerun()

with aba_kanban:
    st.markdown("### Quadro Kanban")
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    status_cols = {"Não iniciada": col_k1, "Em andamento": col_k2, "Travada": col_k3, "Concluída": col_k4}
    
    col_k1.error("Não iniciada")
    col_k2.warning("Em andamento")
    col_k3.error("Travada")
    col_k4.success("Concluída")
    
    for t in tarefas:
        coluna_alvo = status_cols.get(t.status, col_k1)
        with coluna_alvo:
            with st.container(border=True):
                st.markdown(f"**{t.nome}**")
                st.caption(f"Fase: {t.fase.nome} | Prio: {t.prioridade}")
                # Conta subtarefas para mostrar um indicador visual no Kanban
                qtd_subs = db.query(Subtarefa).filter(Subtarefa.tarefa_id == t.id).count()
                if qtd_subs > 0:
                    st.caption(f"*(Contém {qtd_subs} subtarefas)*")
                st.progress(int(t.percentual_concluido) if t.percentual_concluido else 0)

with aba_subtarefas:
    st.markdown("### 📋 Gestão de Subtarefas")
    st.write("Quebre tarefas complexas em itens menores. O progresso da tarefa principal será calculado automaticamente.")
    
    tarefa_selecionada = st.selectbox("Selecione a Tarefa Mãe:", [t.id for t in tarefas], format_func=lambda x: next(t.nome for t in tarefas if t.id == x) if tarefas else "")
    
    if tarefa_selecionada:
        subs_db = db.query(Subtarefa).filter(Subtarefa.tarefa_id == tarefa_selecionada).order_by(Subtarefa.id).all()
        
        if subs_db:
            st.markdown("#### Checklist")
            for sub in subs_db:
                c_check, c_del = st.columns([0.9, 0.1])
                
                with c_check:
                    marcado = st.checkbox(f"{sub.nome}", value=sub.concluida, key=f"chk_{sub.id}")
                    if marcado != sub.concluida:
                        sub.concluida = marcado
                        db.commit()
                        atualizar_progresso_subtarefas(db, tarefa_selecionada)
                        registrar_acao(db, "Checklist Atualizado", f"Marcou '{sub.nome}' como {'Concluído' if marcado else 'Pendente'}")
                        db.commit()
                        st.rerun()
                        
                with c_del:
                    if st.button("🗑️", key=f"del_sub_{sub.id}", help="Excluir esta subtarefa"):
                        nome_apagado = sub.nome
                        db.delete(sub)
                        db.commit()
                        atualizar_progresso_subtarefas(db, tarefa_selecionada)
                        registrar_acao(db, "Exclusão de Subtarefa", f"Excluiu a subtarefa '{nome_apagado}'")
                        db.commit()
                        st.rerun()
        else:
            st.info("Nenhuma subtarefa cadastrada ainda.")
            
        with st.form("form_nova_sub", clear_on_submit=True):
            nova_sub_nome = st.text_input("Nome da Nova Subtarefa")
            if st.form_submit_button("Adicionar Item"):
                if nova_sub_nome:
                    nova_sub = Subtarefa(tarefa_id=tarefa_selecionada, nome=nova_sub_nome)
                    db.add(nova_sub)
                    db.commit()
                    atualizar_progresso_subtarefas(db, tarefa_selecionada)
                    registrar_acao(db, "Nova Subtarefa", f"Adicionou '{nova_sub_nome}' à tarefa ID {tarefa_selecionada}")
                    db.commit()
                    st.rerun()

st.divider()

# --- 3. FERRAMENTAS DE GESTÃO (ADICIONAR, EDITAR, EXCLUIR) ---

with st.expander("➕ Adicionar Nova Tarefa", expanded=False):
    with st.form("form_nova_tarefa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nova_nome = c1.text_input("Nome da Tarefa *")
        nova_fase = c2.selectbox("Fase *", [f.id for f in fases_db], format_func=lambda x: next(f.nome for f in fases_db if f.id == x) if fases_db else "")
        nova_inicio = c1.date_input("Data Início", datetime.date.today(), format="DD/MM/YYYY")
        nova_fim = c2.date_input("Data Término", datetime.date.today() + datetime.timedelta(days=7), format="DD/MM/YYYY")
        
        if st.form_submit_button("Criar Tarefa"):
            if not nova_nome or not nova_fase:
                st.error("Nome e Fase são obrigatórios.")
            else:
                t = Tarefa(fase_id=nova_fase, nome=nova_nome, data_inicio=nova_inicio, data_termino=nova_fim, status="Não iniciada")
                db.add(t)
                db.commit()
                registrar_acao(db, "Nova Tarefa", f"Criou a tarefa '{nova_nome}'")
                db.commit()
                st.success("Tarefa adicionada!")
                st.rerun()

with st.expander("➕ Adicionar Nova Fase", expanded=False):
    with st.form("form_nova_fase", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        nova_fase_nome = c1.text_input("Nome da Nova Fase *", placeholder="Ex: 15. Ampliação da Subestação")
        nova_fase_ordem = c2.number_input("Ordem (Posição)", min_value=1, value=len(fases_db) + 1)
        
        if st.form_submit_button("Criar Fase"):
            if nova_fase_nome:
                nova_fase_obj = Fase(projeto_id=projeto_id, nome=nova_fase_nome, ordem=nova_fase_ordem)
                db.add(nova_fase_obj)
                db.commit()
                registrar_acao(db, "Nova Fase", f"Criou a fase '{nova_fase_nome}'")
                db.commit()
                st.success("Fase criada com sucesso!")
                st.rerun()

with st.expander("✏️ Editar ou Excluir Fase", expanded=False):
    if fases_db:
        with st.form("form_editar_fase", clear_on_submit=True):
            fase_selecionada_id = st.selectbox("Selecione a fase:", [f.id for f in fases_db], format_func=lambda x: next(f.nome for f in fases_db if f.id == x))
            c_edit1, c_edit2 = st.columns([3, 1])
            novo_nome_fase = c_edit1.text_input("Renomear para:", placeholder="Deixe em branco para manter")
            st.warning("⚠️ Se excluir, **TODAS as tarefas** dela serão apagadas!")
            
            c_btn1, c_btn2 = st.columns(2)
            btn_salvar_fase = c_btn1.form_submit_button("💾 Salvar Novo Nome", type="primary")
            btn_excluir_fase = c_btn2.form_submit_button("🗑️ Excluir Fase Inteira")
            
            if btn_salvar_fase and novo_nome_fase:
                fase_db = db.query(Fase).filter(Fase.id == fase_selecionada_id).first()
                nome_antigo = fase_db.nome
                fase_db.nome = novo_nome_fase
                db.commit()
                registrar_acao(db, "Edição de Fase", f"Renomeou '{nome_antigo}' para '{novo_nome_fase}'")
                db.commit()
                st.success("Renomeada com sucesso!")
                st.rerun()
            
            if btn_excluir_fase:
                fase_db = db.query(Fase).filter(Fase.id == fase_selecionada_id).first()
                nome_fase = fase_db.nome
                db.delete(fase_db)
                db.commit()
                registrar_acao(db, "Exclusão de Fase", f"Excluiu a fase '{nome_fase}'")
                db.commit()
                st.success("Fase excluída!")
                st.rerun()

with st.expander("🗑️ Excluir Tarefa", expanded=False):
    with st.form("form_excluir_tarefa"):
        st.warning("Atenção: Exclusão definitiva (apagará subtarefas também).")
        tarefa_para_excluir = st.selectbox("Selecione a tarefa:", [t.id for t in tarefas], format_func=lambda x: next(f"[{t.fase.nome}] {t.nome}" for t in tarefas if t.id == x) if tarefas else "")
        
        if st.form_submit_button("Excluir Definitivamente"):
            if tarefa_para_excluir:
                tarefa_db = db.query(Tarefa).filter(Tarefa.id == tarefa_para_excluir).first()
                nome_tarefa = tarefa_db.nome
                db.delete(tarefa_db)
                db.commit()
                registrar_acao(db, "Exclusão de Tarefa", f"Excluiu a tarefa '{nome_tarefa}'")
                db.commit()
                st.success("Tarefa excluída!")
                st.rerun()
