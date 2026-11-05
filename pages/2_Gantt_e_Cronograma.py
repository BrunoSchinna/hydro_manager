import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from database import SessionLocal
from models import Projeto, Tarefa, Fase, Dependencia, Historico
from services.cronograma import recalcular_datas_sucessoras

st.set_page_config(page_title="Gantt e Cronograma", page_icon="📊", layout="wide")

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
    st.divider()

# Verifica se há um projeto ativo na sessão
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

st.title(f"📊 Cronograma Gantt: {projeto.nome}")

# Busca as tarefas ordenadas por fase e data
tarefas = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == projeto_id).order_by(Fase.ordem, Tarefa.data_inicio).all()

if not tarefas:
    st.info("Nenhuma tarefa para exibir no cronograma. Adicione tarefas no Painel de Tarefas.")
    st.stop()

# --- 1. PREPARAÇÃO DOS DADOS PARA O PLOTLY GANTT ---
dados_gantt = []
hoje = datetime.date.today()

for t in tarefas:
    # Lógica de destaque: Tarefa atrasada se a data de término passou e não está concluída
    atrasada = t.data_termino and t.data_termino < hoje and t.status != "Concluída"
    cor_status = "Atrasada (Crítico)" if atrasada else t.status
    
    dados_gantt.append({
        "Tarefa": t.nome,
        "Início": t.data_inicio,
        "Término": t.data_termino,
        "Fase": t.fase.nome,
        "Status": cor_status,
        "Concluído (%)": t.percentual_concluido,
        "Responsável": t.responsavel or "Não atribuído" # Incluindo o responsável no gráfico!
    })

df_gantt = pd.DataFrame(dados_gantt)

# Cria colunas de texto formatado exclusivamente para o hover (caixa flutuante do mouse)
df_gantt["Início (BR)"] = pd.to_datetime(df_gantt["Início"]).dt.strftime("%d/%m/%Y")
df_gantt["Término (BR)"] = pd.to_datetime(df_gantt["Término"]).dt.strftime("%d/%m/%Y")

# Mapeamento de cores personalizado
cores = {
    "Não iniciada": "#3498db",  # Azul
    "Em andamento": "#f39c12",  # Laranja
    "Travada": "#8e44ad",       # Roxo
    "Concluída": "#2ecc71",     # Verde
    "Atrasada (Crítico)": "#e74c3c" # Vermelho
}

fig = px.timeline(
    df_gantt, 
    x_start="Início", 
    x_end="Término", 
    y="Tarefa", 
    color="Status",
    color_discrete_map=cores,
    facet_row="Fase",
    text="Responsável", # Faz o nome do responsável aparecer escrito DENTRO da barra colorida
    # Customiza a caixa de hover
    hover_data={"Início": False, "Término": False, "Início (BR)": True, "Término (BR)": True, "Concluído (%)": True, "Responsável": True}
)
fig.update_yaxes(autorange="reversed")
fig.update_layout(height=600, showlegend=True, margin=dict(l=20, r=20, t=40, b=20))

# Força o eixo X a exibir no padrão brasileiro
fig.update_xaxes(tickformat="%d/%m/%Y")

# Adiciona a linha do dia atual
fig.add_vline(x=pd.Timestamp(hoje).timestamp() * 1000, line_width=2, line_dash="dash", line_color="red", annotation_text="Hoje")

st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 2. GESTÃO DE DEPENDÊNCIAS ---
st.subheader("🔗 Gerenciar Dependências")
st.write("Defina qual tarefa deve terminar para que a próxima possa começar. O sistema ajustará as datas automaticamente se a predecessora atrasar.")

col_dep1, col_dep2, col_dep3 = st.columns([2, 2, 1])

# Dicionário mapeando Nome -> ID para o selectbox
mapa_tarefas = {f"[{t.fase.nome}] {t.nome}": t.id for t in tarefas}
opcoes_tarefas = list(mapa_tarefas.keys())

predecessora_sel = col_dep1.selectbox("Tarefa Predecessora (Deve terminar primeiro)", opcoes_tarefas)
sucessora_sel = col_dep2.selectbox("Tarefa Sucessora (Começa depois)", opcoes_tarefas)

if col_dep3.button("Criar Dependência", use_container_width=True, type="primary"):
    id_pred = mapa_tarefas[predecessora_sel]
    id_suc = mapa_tarefas[sucessora_sel]
    
    if id_pred == id_suc:
        st.error("Uma tarefa não pode ser dependente dela mesma.")
    else:
        existe = db.query(Dependencia).filter_by(tarefa_predecessora_id=id_pred, tarefa_sucessora_id=id_suc).first()
        if existe:
            st.warning("Essa dependência já existe!")
        else:
            nova_dep = Dependencia(tarefa_predecessora_id=id_pred, tarefa_sucessora_id=id_suc)
            db.add(nova_dep)
            
            # Registra no histórico
            usuario = st.session_state.get('usuario_nome', 'Sistema')
            log = Historico(usuario=usuario, acao="Nova Dependência", detalhes=f"[Projeto: {projeto.nome}] Ligou: {predecessora_sel} ➡️ {sucessora_sel}")
            db.add(log)
            
            db.commit()
            recalcular_datas_sucessoras(db, id_pred)
            st.success("Dependência criada! As datas foram ajustadas.")
            st.rerun()

# --- EXCLUIR DEPENDÊNCIA ---
with st.expander("🗑️ Excluir Dependência Existente", expanded=False):
    deps_do_projeto = db.query(Dependencia).join(Tarefa, Dependencia.tarefa_predecessora_id == Tarefa.id).join(Fase).filter(Fase.projeto_id == projeto_id).all()
    
    if not deps_do_projeto:
        st.info("Nenhuma dependência cadastrada neste projeto.")
    else:
        with st.form("form_excluir_dep"):
            st.write("Selecione o vínculo que deseja remover:")
            
            opcoes_dep = {d.id: f"{d.predecessora.nome} ➡️ {d.sucessora.nome}" for d in deps_do_projeto}
            dep_selecionada = st.selectbox("Dependência a ser excluída:", options=list(opcoes_dep.keys()), format_func=lambda x: opcoes_dep[x])
            
            if st.form_submit_button("Excluir Vínculo"):
                dep_db = db.query(Dependencia).filter(Dependencia.id == dep_selecionada).first()
                if dep_db:
                    texto_dep = opcoes_dep[dep_selecionada]
                    db.delete(dep_db)
                    
                    usuario = st.session_state.get('usuario_nome', 'Sistema')
                    log = Historico(usuario=usuario, acao="Exclusão de Dependência", detalhes=f"[Projeto: {projeto.nome}] Removeu o vínculo: {texto_dep}")
                    db.add(log)
                    
                    db.commit()
                    st.success("Dependência excluída com sucesso!")
                    st.rerun()
