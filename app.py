import streamlit as st
from database import SessionLocal
from models import Projeto, Tarefa, Fase, Documento
from services.seed import init_db
from sqlalchemy import text

st.set_page_config(page_title="Hydro Manager", page_icon="🌊", layout="wide")

@st.cache_resource
def iniciar_banco_uma_vez():
    init_db()
    
    db_atualizacao = SessionLocal()
    try:
        db_atualizacao.execute(text("ALTER TABLE tarefas ADD COLUMN responsavel VARCHAR DEFAULT 'Não atribuído';"))
        db_atualizacao.commit()
    except Exception:
        db_atualizacao.rollback()
        
    try:
        db_atualizacao.execute(text("ALTER TABLE dependencias ADD COLUMN tipo VARCHAR DEFAULT 'Fim-Início';"))
        db_atualizacao.commit()
    except Exception:
        db_atualizacao.rollback()
        
    # --- NOVO: Tenta criar a tabela de documentos se ela não existir ---
    try:
        Documento.__table__.create(bind=db_atualizacao.get_bind(), checkfirst=True)
    except Exception:
        pass
        
    finally:
        db_atualizacao.close()
        
    return True

iniciar_banco_uma_vez()

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""

def checar_credenciais(usuario_digitado, senha_digitada):
    try:
        if "usuarios" in st.secrets:
            usuarios_validos = st.secrets["usuarios"]
            if usuario_digitado in usuarios_validos and usuarios_validos[usuario_digitado] == senha_digitada:
                return True
    except Exception:
        pass
    return False

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

with st.sidebar:
    st.write(f"👤 Conectado como: **{st.session_state['usuario_nome']}**")
    if st.button("🚪 Sair (Logout)", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["usuario_nome"] = ""
        st.rerun()

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

db = get_db()

st.title("🌊 Hydro Manager")
st.write("Gestão de Projetos e Engenharia de Usinas Hidrelétricas")

with st.expander("➕ Novo Projeto", expanded=False):
    with st.form("form_novo_projeto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Projeto *")
        tipo = col2.selectbox("Tipo *", ["UHE", "PCH", "CGH"])
        rio = col1.text_input("Rio")
        pot = col2.number_input("Potência (MW)", min_value=0.0, format="%.2f")
        usar_template = st.checkbox("Carregar cronograma padrão para Hidrelétricas (14 Fases)", value=True)
        
        if st.form_submit_button("Salvar Projeto", type="primary"):
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
                
                tarefas_projeto = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == proj.id).all()
                if tarefas_projeto:
                    media_progresso = sum((100 if t.status == "Concluída" else (t.percentual_concluido or 0)) for t in tarefas_projeto) / len(tarefas_projeto)
                else:
                    media_progresso = 0.0
                
                st.progress(int(media_progresso), text=f"Progresso Geral: {int(media_progresso)}%") 
                
                # --- NOVA GAVETA DE ANEXOS DO PROJETO ---
                with st.expander("📂 Documentos e Links"):
                    docs = db.query(Documento).filter(Documento.projeto_id == proj.id).all()
                    
                    if docs:
                        for d in docs:
                            # Monta o link clicável e um botão de lixeira ao lado
                            c_link, c_del = st.columns([0.8, 0.2])
                            c_link.markdown(f"🔗 [{d.nome}]({d.url})")
                            if c_del.button("🗑️", key=f"del_doc_{d.id}", help="Excluir link"):
                                db.delete(d)
                                db.commit()
                                st.rerun()
                    else:
                        st.caption("Nenhum anexo salvo ainda.")
                        
                    with st.form(f"form_doc_{proj.id}", clear_on_submit=True):
                        st.write("**Novo Anexo**")
                        doc_nome = st.text_input("Nome (Ex: Planta Baixa)", key=f"nome_doc_{proj.id}")
                        doc_url = st.text_input("Link (G. Drive, OneDrive)", key=f"url_doc_{proj.id}")
                        if st.form_submit_button("Salvar Link"):
                            if doc_nome and doc_url:
                                novo_doc = Documento(projeto_id=proj.id, nome=doc_nome, url=doc_url)
                                db.add(novo_doc)
                                db.commit()
                                st.rerun()
                            else:
                                st.error("Preencha o nome e o link.")
                
                c1, c2 = st.columns(2)
                if c1.button("Abrir Painel", key=f"abrir_{proj.id}", use_container_width=True):
                    st.session_state['projeto_ativo_id'] = proj.id
                    st.switch_page("pages/1_Painel_de_Tarefas.py")
                    
                if c2.button("Excluir", key=f"del_{proj.id}", use_container_width=True):
                    db.delete(proj)
                    db.commit()
                    st.rerun()
