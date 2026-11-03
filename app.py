import streamlit as st
from database import SessionLocal
from models import Projeto, Tarefa, Fase
from services.seed import init_db

# Configuração da página (deve ser o primeiro comando do Streamlit)
st.set_page_config(page_title="Hydro Manager", page_icon="🌊", layout="wide")

# --- OTIMIZAÇÃO DE PERFORMANCE (CACHE) ---
@st.cache_resource
def iniciar_banco_uma_vez():
    init_db()
    return True

iniciar_banco_uma_vez()

# --- CONTROLE DE SESSÃO / AUTENTICAÇÃO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""

def checar_credenciais(usuario_digitado, senha_digitada):
    # 1. Fallback de emergência (agora vem primeiro e nunca falha)
    if usuario_digitado == "admin" and senha_digitada == "hydro123":
        return True
        
    # 2. Tenta ler o arquivo de senhas do Render com segurança
    try:
        if "usuarios" in st.secrets:
            usuarios_validos = st.secrets["usuarios"]
            if usuario_digitado in usuarios_validos and usuarios_validos[usuario_digitado] == senha_digitada:
                return True
    except Exception:
        pass # Se o arquivo não existir, o sistema ignora o erro sem "crashar"
        
    return False

# Tela de Login (bloqueia o resto do app se não estiver logado)
if not st.session_state["autenticado"]:
    st.title("🔒 Hydro Manager - Acesso Restrito")
    st.write("")
    
    col_vazia1, col_login, col_vazia2 = st.columns([1, 1.2, 1])
    
    with col_login:
        with st.container(border=True):
            st.subheader("Login de Colaborador")
            user = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            
            if st.button("Entrar", type="primary", use_container_width=True):
                if checar_credenciais(user.strip(), senha.strip()):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_nome"] = user.strip()
                    st.success("Autenticado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
                    
    st.stop()

# --- INTERFACE DA TELA INICIAL (SISTEMA LIBERADO) ---

# Barra lateral
with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state['usuario_nome']}**")
    if st.button("🚪 Sair (Logout)", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["usuario_nome"] = ""
        st.rerun()

# Função auxiliar para gerenciar a conexão com o banco
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

db = get_db()

st.title("🌊 Hydro Manager")
st.write("Gestão de Projetos e Engenharia de Usinas Hidrelétricas")

# Formulário para criar novo projeto
with st.expander("➕ Novo Projeto", expanded=False):
    with st.form("form_novo_projeto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Projeto *")
        tipo = col2.selectbox("Tipo *", ["UHE", "PCH", "CGH"])
        rio = col1.text_input("Rio")
        pot = col2.number_input("Potência (MW)", min_value=0.0, format="%.2f")
        
        usar_template = st.checkbox("Carregar cronograma padrão para Hidrelétricas (14 Fases)", value=True)
        
        submit = st.form_submit_button("Salvar Projeto", type="primary")
        
        if submit:
            if not nome:
                st.error("O nome do projeto é obrigatório.")
            else:
                novo_proj = Projeto(nome=nome, tipo=tipo, rio=rio, potencia_mw=pot)
                db.add(novo_proj)
                db.commit()
                db.refresh(novo_proj)
                
                if usar_template:
                    from services.template_hydro import aplicar_template_hydro
                    aplicar_template_hydro(db, novo_proj.id)
                
                st.success(f"Projeto {nome} criado com sucesso!")
                st.rerun()

st.divider()
st.subheader("Projetos Ativos")

projetos = db.query(Projeto).all()

if not projetos:
    st.info("Nenhum projeto encontrado.")
else:
    cols = st.columns(3)
    
    for i, proj in enumerate(projetos):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {proj.nome}")
                st.write(f"**Tipo:** {proj.tipo} | **Potência:** {proj.potencia_mw} MW")
                st.write(f"📍 {proj.municipio_uf or 'Local não definido'} - Rio {proj.rio or 'Não definido'}")
                
                # --- CÁLCULO DE PROGRESSO REAL ---
                tarefas_projeto = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == proj.id).all()
                if tarefas_projeto:
                    media_progresso = sum(t.percentual_concluido or 0 for t in tarefas_projeto) / len(tarefas_projeto)
                else:
                    media_progresso = 0.0
                
                st.progress(int(media_progresso), text=f"Progresso Geral: {int(media_progresso)}%") 
                
                c1, c2 = st.columns(2)
                if c1.button("Abrir Painel", key=f"abrir_{proj.id}", use_container_width=True):
                    st.session_state['projeto_ativo_id'] = proj.id
                    st.switch_page("pages/1_Painel_de_Tarefas.py")
                    
                if c2.button("Excluir", key=f"del_{proj.id}", use_container_width=True):
                    db.delete(proj)
                    db.commit()
                    st.rerun()
