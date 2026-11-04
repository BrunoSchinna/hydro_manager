import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Historico
import datetime

st.set_page_config(page_title="Histórico de Atividades", page_icon="🕵️", layout="wide")

# --- 0. TRAVA DE SEGURANÇA (AUTENTICAÇÃO) ---
if not st.session_state.get("autenticado", False):
    st.warning("🔒 Acesso restrito. Faça login na página inicial primeiro.")
    st.page_link("app.py", label="⬅️ Ir para a página de Login")
    st.stop()

# Barra lateral
with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state.get('usuario_nome', '')}**")
    st.page_link("app.py", label="🏠 Início / Projetos")
    st.page_link("pages/1_Painel_de_Tarefas.py", label="📋 Painel de Tarefas")
    st.page_link("pages/4_Dashboard.py", label="📈 Dashboard")
    st.divider()

st.title("🕵️ Histórico de Auditoria")
st.write("Acompanhe todas as alterações realizadas no sistema pela sua equipe em tempo real.")
st.divider()

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

db = get_db()

# Busca os registros ordenados do mais recente para o mais antigo
registros_db = db.query(Historico).order_by(Historico.data_hora.desc()).all()

if not registros_db:
    st.info("Nenhuma atividade foi registrada no sistema ainda. Comece a editar projetos e tarefas para popular o histórico.")
else:
    # --- 1. ÁREA DE FILTROS ---
    st.subheader("Filtros de Busca")
    col1, col2 = st.columns(2)
    
    # Extrai listas únicas de usuários e ações para os menus suspensos
    usuarios_unicos = ["Todos"] + sorted(list(set(r.usuario for r in registros_db)))
    acoes_unicas = ["Todas"] + sorted(list(set(r.acao for r in registros_db)))
    
    filtro_usuario = col1.selectbox("Filtrar por Usuário", usuarios_unicos)
    filtro_acao = col2.selectbox("Filtrar por Ação", acoes_unicas)
    
    # --- 2. PREPARAÇÃO DOS DADOS ---
    dados = []
    for r in registros_db:
        # Aplica os filtros escolhidos pela diretoria
        if filtro_usuario != "Todos" and r.usuario != filtro_usuario:
            continue
        if filtro_acao != "Todas" and r.acao != filtro_acao:
            continue
            
        # Formata a data para o padrão brasileiro
        data_hora_formatada = r.data_hora.strftime("%d/%m/%Y %H:%M:%S") if r.data_hora else ""
        
        dados.append({
            "Data e Hora": data_hora_formatada,
            "Usuário": r.usuario,
            "Ação": r.acao,
            "Detalhes": r.detalhes
        })
        
    df = pd.DataFrame(dados)
    
    # --- 3. EXIBIÇÃO DA TABELA ---
    if df.empty:
        st.warning("Nenhum registro encontrado com os filtros selecionados.")
    else:
        # Mostra a tabela limpa e bloqueada para edição (afinal, é auditoria!)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        st.write("") # Espaçamento
        
        # Botão para baixar o histórico
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Baixar Histórico Completo (.csv)",
            data=csv,
            file_name=f"Auditoria_HydroManager_{datetime.date.today().strftime('%d_%m_%Y')}.csv",
            mime="text/csv",
        )
