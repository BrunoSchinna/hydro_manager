import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
from database import SessionLocal
from models import Projeto, Tarefa, Fase

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")

# --- 0. TRAVA DE SEGURANÇA (AUTENTICAÇÃO) ---
if not st.session_state.get("autenticado", False):
    st.warning("🔒 Acesso restrito. Faça login na página inicial primeiro.")
    st.page_link("app.py", label="⬅️ Ir para a página de Login")
    st.stop()

# Barra lateral com identificação e navegação
with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state.get('usuario_nome', '')}**")
    st.page_link("app.py", label="🏠 Início / Projetos")
    st.page_link("pages/1_Painel_de_Tarefas.py", label="📋 Painel de Tarefas")
    st.page_link("pages/2_Gantt_e_Cronograma.py", label="📊 Gantt")
    st.page_link("pages/3_Fluxograma.py", label="🕸️ Fluxograma")
    st.divider()

if 'projeto_ativo_id' not in st.session_state:
    st.warning("Nenhum projeto selecionado.")
    st.page_link("app.py", label="⬅️ Voltar para a Página Inicial")
    st.stop()

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

db = get_db()
projeto_id = st.session_state['projeto_ativo_id']
projeto = db.query(Projeto).filter(Projeto.id == projeto_id).first()

st.title(f"📈 Dashboard e Relatórios: {projeto.nome}")
st.divider()

tarefas = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == projeto_id).all()

if not tarefas:
    st.info("O projeto ainda não possui tarefas para gerar o Dashboard.")
    st.stop()

# --- 1. CÁLCULO DAS MÉTRICAS ---
hoje = datetime.date.today()
total_tarefas = len(tarefas)
tarefas_concluidas = sum(1 for t in tarefas if t.status == "Concluída")
tarefas_atrasadas = sum(1 for t in tarefas if t.data_termino and t.data_termino < hoje and t.status != "Concluída")
prox_7_dias = sum(1 for t in tarefas if t.data_termino and hoje <= t.data_termino <= hoje + datetime.timedelta(days=7) and t.status != "Concluída")

# Progresso geral (Média simples do % concluído)
progresso_medio = sum(t.percentual_concluido or 0 for t in tarefas) / total_tarefas if total_tarefas > 0 else 0

# --- 2. EXIBIÇÃO DOS CARDS (MÉTRICAS) ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Tarefas", total_tarefas)
c2.metric("Avanço Global", f"{progresso_medio:.1f}%")
c3.metric("Tarefas Atrasadas", tarefas_atrasadas, delta_color="inverse")
c4.metric("Entregas (Próx 7 dias)", prox_7_dias)

st.divider()

# --- 3. GRÁFICOS ---
col_g1, col_g2 = st.columns(2)

# Gráfico 1: Status das Tarefas
status_contagem = pd.Series([t.status for t in tarefas]).value_counts().reset_index()
status_contagem.columns = ["Status", "Quantidade"]

cores = {"Não iniciada": "#3498db", "Em andamento": "#f39c12", "Travada": "#8e44ad", "Concluída": "#2ecc71"}
fig_pie = px.pie(status_contagem, names="Status", values="Quantidade", title="Distribuição por Status", color="Status", color_discrete_map=cores, hole=0.4)
col_g1.plotly_chart(fig_pie, use_container_width=True)

# Gráfico 2: Tarefas por Fase
fase_contagem = pd.Series([t.fase.nome for t in tarefas]).value_counts().reset_index()
fase_contagem.columns = ["Fase", "Quantidade"]
fig_bar = px.bar(fase_contagem, x="Quantidade", y="Fase", title="Volume de Tarefas por Fase", orientation='h')
fig_bar.update_yaxes(autorange="reversed")
col_g2.plotly_chart(fig_bar, use_container_width=True)

# --- 4. EXPORTAÇÃO DE RELATÓRIO EXCEL ---
st.subheader("📥 Exportação de Dados")
st.write("Baixe a lista completa de tarefas deste projeto para usar em planilhas ou enviar por e-mail.")

dados_export = []
for t in tarefas:
    dados_export.append({
        "Fase": t.fase.nome,
        "ID": t.id,
        "Nome da Tarefa": t.nome,
        "Status": t.status,
        "Prioridade": t.prioridade,
        "Início": t.data_inicio.strftime("%d/%m/%Y") if t.data_inicio else "",
        "Término": t.data_termino.strftime("%d/%m/%Y") if t.data_termino else "",
        "Avanço Físico (%)": t.percentual_concluido,
        "É Marco?": "Sim" if t.is_marco else "Não"
    })

df_export = pd.DataFrame(dados_export)

# Converte o DataFrame do Pandas para um arquivo Excel em memória usando BytesIO
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_export.to_excel(writer, index=False, sheet_name='Tarefas do Projeto')

# Botão nativo do Streamlit para download de arquivo
st.download_button(
    label="⬇️ Baixar Relatório Excel (.xlsx)",
    data=buffer.getvalue(),
    file_name=f"Relatorio_{projeto.nome.replace(' ', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary"
)
