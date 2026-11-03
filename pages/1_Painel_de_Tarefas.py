import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Projeto, Fase, Tarefa, Responsavel
import datetime

st.set_page_config(page_title="Painel de Tarefas", page_icon="📋", layout="wide")

# --- 0. TRAVA DE SEGURANÇA (AUTENTICAÇÃO) ---
if not st.session_state.get("autenticado", False):
    st.warning("🔒 Acesso restrito. Faça login na página inicial primeiro.")
    st.page_link("app.py", label="⬅️ Ir para a página de Login")
    st.stop()

# Barra lateral com identificação
with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state.get('usuario_nome', '')}**")
    st.page_link("app.py", label="🏠 Início / Projetos")
    st.divider()

# Verifica se há um projeto ativo na sessão
if 'projeto_ativo_id' not in st.session_state:
    st.warning("Nenhum projeto selecionado. Volte para a página inicial e escolha um projeto.")
    st.page_link("app.py", label="⬅️ Voltar para a Página Inicial")
    st.stop()

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

db = get_db()
projeto_id = st.session_state['projeto_ativo_id']
projeto = db.query(Projeto).filter(Projeto.id == projeto_id).first()

st.title(f"📋 Painel de Tarefas: {projeto.nome}")
st.page_link("app.py", label="⬅️ Voltar para Projetos")
st.divider()

# --- 1. FILTROS ---
st.subheader("Filtros")
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
busca = col_f1.text_input("🔍 Buscar por nome da tarefa")
filtro_status = col_f2.selectbox("Status", ["Todos", "Não iniciada", "Em andamento", "Travada", "Concluída"])
filtro_prio = col_f3.selectbox("Prioridade", ["Todas", "Baixa", "Média", "Alta", "Crítica"])

# Busca as fases do projeto para o filtro (ordenadas pela coluna 'ordem')
fases_db = db.query(Fase).filter(Fase.projeto_id == projeto_id).order_by(Fase.ordem).all()
opcoes_fase = ["Todas"] + [f.nome for f in fases_db]
filtro_fase = col_f4.selectbox("Fase", opcoes_fase)

# Busca os dados filtrados
query = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == projeto_id)
if busca:
    query = query.filter(Tarefa.nome.ilike(f"%{busca}%"))
if filtro_status != "Todos":
    query = query.filter(Tarefa.status == filtro_status)
if filtro_prio != "Todas":
    query = query.filter(Tarefa.prioridade == filtro_prio)
if filtro_fase != "Todas":
    query = query.filter(Fase.nome == filtro_fase)

# Ordena as tarefas pela ordem da fase e depois pela data de início
tarefas = query.order_by(Fase.ordem, Tarefa.data_inicio).all()

# --- 2. ABAS DE VISUALIZAÇÃO ---
aba_tabela, aba_kanban = st.tabs(["📝 Tabela de Tarefas", "🗂️ Kanban (Quadro)"])

with aba_tabela:
    st.markdown("### Edição Rápida")
    st.write("Edite as informações diretamente na tabela e clique em **Salvar Alterações** no final.")
    
    if not tarefas:
        st.info("Nenhuma tarefa encontrada com os filtros atuais. (Adicione tarefas direto no banco ou aguarde a etapa de criação de templates)")
    else:
        # Monta um DataFrame do Pandas para exibir no data_editor
        dados = []
        for t in tarefas:
            dados.append({
                "ID": t.id,
                "Fase": t.fase.nome,
                "Tarefa": t.nome,
                "Status": t.status,
                "Prioridade": t.prioridade,
                "Início": t.data_inicio,
                "Término": t.data_termino,
                "% Concluído": t.percentual_concluido,
                "Marco?": t.is_marco,
            })
        
        df = pd.DataFrame(dados)
        
        # O st.data_editor permite editar o dataframe na tela
        df_editado = st.data_editor(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", disabled=True),
                "Fase": st.column_config.TextColumn("Fase", disabled=True),
                "Status": st.column_config.SelectboxColumn("Status", options=["Não iniciada", "Em andamento", "Travada", "Concluída"]),
                "Prioridade": st.column_config.SelectboxColumn("Prioridade", options=["Baixa", "Média", "Alta", "Crítica"]),
                "Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Término": st.column_config.DateColumn("Término", format="DD/MM/YYYY"),
                "% Concluído": st.column_config.ProgressColumn("% Concluído", min_value=0.0, max_value=100.0, format="%f%%"),
            },
            hide_index=True,
            use_container_width=True,
            key="editor_tarefas"
        )
        
        # Botão para salvar alterações do DataFrame de volta pro Banco de Dados
        if st.button("💾 Salvar Alterações da Tabela", type="primary"):
            for index, row in df_editado.iterrows():
                tarefa_db = db.query(Tarefa).filter(Tarefa.id == row["ID"]).first()
                if tarefa_db:
                    tarefa_db.nome = row["Tarefa"]
                    tarefa_db.status = row["Status"]
                    tarefa_db.prioridade = row["Prioridade"]
                    tarefa_db.data_inicio = row["Início"]
                    tarefa_db.data_termino = row["Término"]
                    tarefa_db.percentual_concluido = row["% Concluído"]
                    tarefa_db.is_marco = row["Marco?"]
            db.commit()
            st.success("Alterações salvas com sucesso!")
            st.rerun()

with aba_kanban:
    st.markdown("### Quadro Kanban")
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    status_cols = {
        "Não iniciada": col_k1,
        "Em andamento": col_k2,
        "Travada": col_k3,
        "Concluída": col_k4
    }
    
    # Cabeçalhos do Kanban
    col_k1.error("Não iniciada")   # Vermelho claro
    col_k2.warning("Em andamento") # Amarelo
    col_k3.error("Travada")        # Usando erro também para travas
    col_k4.success("Concluída")    # Verde
    
    for t in tarefas:
        coluna_alvo = status_cols.get(t.status, col_k1)
        with coluna_alvo:
            with st.container(border=True):
                st.markdown(f"**{t.nome}**")
                st.caption(f"Fase: {t.fase.nome}")
                st.caption(f"Prio: {t.prioridade}")
                st.progress(int(t.percentual_concluido) if t.percentual_concluido else 0)

st.divider()

# --- 3. FERRAMENTAS DE GESTÃO (ADICIONAR, EDITAR, EXCLUIR) ---

# Bloco simples para adicionar uma nova tarefa solta
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
            elif nova_fim < nova_inicio:
                st.error("A data de término não pode ser anterior à data de início.")
            else:
                t = Tarefa(
                    fase_id=nova_fase,
                    nome=nova_nome,
                    data_inicio=nova_inicio,
                    data_termino=nova_fim,
                    status="Não iniciada"
                )
                db.add(t)
                db.commit()
                st.success("Tarefa adicionada!")
                st.rerun()

# Bloco para adicionar uma nova fase
with st.expander("➕ Adicionar Nova Fase", expanded=False):
    with st.form("form_nova_fase", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        nova_fase_nome = c1.text_input("Nome da Nova Fase *", placeholder="Ex: 15. Ampliação da Subestação")
        nova_fase_ordem = c2.number_input("Ordem (Posição)", min_value=1, value=len(fases_db) + 1)
        
        if st.form_submit_button("Criar Fase"):
            if not nova_fase_nome:
                st.error("O nome da fase é obrigatório.")
            else:
                nova_fase_obj = Fase(projeto_id=projeto_id, nome=nova_fase_nome, ordem=nova_fase_ordem)
                db.add(nova_fase_obj)
                db.commit()
                st.success("Fase criada com sucesso!")
                st.rerun()

# Bloco para Editar ou Excluir uma Fase
with st.expander("✏️ Editar ou Excluir Fase", expanded=False):
    if not fases_db:
        st.info("Não há fases para editar.")
    else:
        with st.form("form_editar_fase", clear_on_submit=True):
            fase_selecionada_id = st.selectbox("Selecione a fase:", [f.id for f in fases_db], format_func=lambda x: next(f.nome for f in fases_db if f.id == x))
            
            c_edit1, c_edit2 = st.columns([3, 1])
            novo_nome_fase = c_edit1.text_input("Renomear para:", placeholder="Deixe em branco para manter o mesmo nome")
            
            st.warning("⚠️ Se você clicar em 'Excluir Fase', **TODAS as tarefas** que pertencem a ela serão apagadas junto!")
            
            c_btn1, c_btn2 = st.columns(2)
            btn_salvar_fase = c_btn1.form_submit_button("💾 Salvar Novo Nome", type="primary")
            btn_excluir_fase = c_btn2.form_submit_button("🗑️ Excluir Fase Inteira")
            
            if btn_salvar_fase:
                if novo_nome_fase:
                    fase_db = db.query(Fase).filter(Fase.id == fase_selecionada_id).first()
                    fase_db.nome = novo_nome_fase
                    db.commit()
                    st.success("Fase renomeada com sucesso!")
                    st.rerun()
            
            if btn_excluir_fase:
                fase_db = db.query(Fase).filter(Fase.id == fase_selecionada_id).first()
                if fase_db:
                    db.delete(fase_db)
                    db.commit()
                    st.success("Fase e suas tarefas foram excluídas!")
                    st.rerun()

# Bloco para excluir uma tarefa
with st.expander("🗑️ Excluir Tarefa", expanded=False):
    with st.form("form_excluir_tarefa"):
        st.warning("Atenção: A exclusão é definitiva e apagará também as dependências ligadas a esta tarefa.")
        
        # Cria uma lista de opções para o selectbox
        opcoes_exclusao = [t.id for t in tarefas]
        
        tarefa_para_excluir = st.selectbox(
            "Selecione a tarefa que deseja excluir:", 
            options=opcoes_exclusao, 
            format_func=lambda x: next(f"[{t.fase.nome}] {t.nome}" for t in tarefas if t.id == x) if tarefas else ""
        )
        
        if st.form_submit_button("Excluir Definitivamente"):
            if tarefa_para_excluir:
                tarefa_db = db.query(Tarefa).filter(Tarefa.id == tarefa_para_excluir).first()
                if tarefa_db:
                    db.delete(tarefa_db)
                    db.commit()
                    st.success("Tarefa excluída com sucesso!")
                    st.rerun()
