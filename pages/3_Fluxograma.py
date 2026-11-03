import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import datetime
from database import SessionLocal
from models import Projeto, Tarefa, Fase, Dependencia

st.set_page_config(page_title="Fluxograma do Projeto", page_icon="🕸️", layout="wide")

# --- 0. TRAVA DE SEGURANÇA (AUTENTICAÇÃO) ---
if not st.session_state.get("autenticado", False):
    st.warning("🔒 Acesso restrito. Faça login na página inicial primeiro.")
    st.page_link("app.py", label="⬅️ Ir para a página de Login")
    st.stop()

# Barra lateral com identificação
with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state.get('usuario_nome', '')}**")
    st.page_link("app.py", label="🏠 Início / Projetos")
    st.page_link("pages/1_Painel_de_Tarefas.py", label="📋 Painel de Tarefas")
    st.page_link("pages/2_Gantt_e_Cronograma.py", label="📊 Gantt e Cronograma")
    st.divider()

if 'projeto_ativo_id' not in st.session_state:
    st.warning("Nenhum projeto selecionado.")
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

st.title(f"🕸️ Fluxograma de Dependências: {projeto.nome}")

st.markdown("""
Aqui você visualiza a rede de dependências do projeto. 
- Arraste os nós para reorganizar a visualização.
- Use o scroll do mouse para dar zoom.
""")

# Busca as tarefas e dependências do projeto ativo
tarefas = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == projeto_id).all()

if not tarefas:
    st.info("Nenhuma tarefa cadastrada neste projeto.")
    st.stop()

deps_cadastradas = db.query(Dependencia).join(Tarefa, Dependencia.tarefa_predecessora_id == Tarefa.id)\
                     .filter(Tarefa.fase.has(projeto_id=projeto_id)).all()

# --- CONSTRUÇÃO DOS NÓS (NODES) E ARESTAS (EDGES) ---
nodes = []
edges = []

hoje = datetime.date.today()

# Define as cores baseadas no status
def obter_cor(tarefa):
    if tarefa.data_termino and tarefa.data_termino < hoje and tarefa.status != "Concluída":
        return "#e74c3c" # Vermelho (Atrasada)
    
    cores_status = {
        "Não iniciada": "#3498db",  # Azul
        "Em andamento": "#f39c12",  # Laranja
        "Travada": "#8e44ad",       # Roxo
        "Concluída": "#2ecc71",     # Verde
    }
    return cores_status.get(tarefa.status, "#95a5a6")

for t in tarefas:
    cor = obter_cor(t)
    # Quebra de linha no label para não ficar um texto muito comprido no nó
    label_formatado = f"[{t.fase.nome}]\n{t.nome}"
    
    nodes.append(Node(
        id=str(t.id),
        label=label_formatado,
        size=25,
        color=cor,
        shape="box",
        font={"color": "white", "size": 14}
    ))

for d in deps_cadastradas:
    edges.append(Edge(
        source=str(d.tarefa_predecessora_id),
        target=str(d.tarefa_sucessora_id),
        color="#7f8c8d",
        arrows="to"
    ))

if not edges and len(nodes) > 0:
    st.info("As tarefas não possuem dependências criadas ainda. Volte à tela do Gantt para conectá-las.")

# --- CONFIGURAÇÃO E RENDERIZAÇÃO DO GRAFO ---
config = Config(
    width="100%",
    height=600,
    directed=True, 
    physics=True, 
    hierarchical=False, # Mude para True se quiser uma árvore rígida de cima para baixo
    nodeHighlightBehavior=True,
    highlightColor="#F7A7A6", 
    collapsible=False
)

st.divider()

# Renderiza o grafo interativo na tela
retorno = agraph(nodes=nodes, edges=edges, config=config)

# Legenda das cores
st.markdown("""
**Legenda:**
🟢 Concluída | 🔵 Não iniciada | 🟠 Em andamento | 🟣 Travada | 🔴 Atrasada (Crítico)
""")
