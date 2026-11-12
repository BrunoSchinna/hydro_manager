import streamlit as st
import json
import datetime
from database import SessionLocal
from models import Projeto, Tarefa, Fase, Documento, Subtarefa, Dependencia
from services.seed import init_db
from sqlalchemy import text

st.set_page_config(page_title="Hydro Manager", page_icon="🌊", layout="wide")

@st.cache_resource
def iniciar_banco_uma_vez():
    db_atualizacao = SessionLocal()
    
    # 1º PASSO: INJETAR AS COLUNAS ANTES DE QUALQUER BUSCA NO BANCO
    try:
        db_atualizacao.execute(text("ALTER TABLE tarefas ADD COLUMN responsavel VARCHAR DEFAULT 'Não atribuído';"))
        db_atualizacao.commit()
    except: db_atualizacao.rollback()
    
    try:
        db_atualizacao.execute(text("ALTER TABLE dependencias ADD COLUMN tipo VARCHAR DEFAULT 'Fim-Início';"))
        db_atualizacao.commit()
    except: db_atualizacao.rollback()
    
    try:
        # Cria a coluna concluido antes do init_db() tentar buscar os projetos!
        db_atualizacao.execute(text("ALTER TABLE projetos ADD COLUMN concluido BOOLEAN DEFAULT FALSE;"))
        db_atualizacao.commit()
    except: db_atualizacao.rollback()
    
    try:
        Documento.__table__.create(bind=db_atualizacao.get_bind(), checkfirst=True)
    except: pass
    
    finally:
        db_atualizacao.close()
        
    # 2º PASSO: AGORA SIM, COM O BANCO PRONTO, RODAMOS A INICIALIZAÇÃO
    init_db()
    
    return True

iniciar_banco_uma_vez()

# --- AUTENTICAÇÃO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_nome"] = ""

def checar_credenciais(usuario_digitado, senha_digitada):
    try:
        if "usuarios" in st.secrets:
            usuarios_validos = st.secrets["usuarios"]
            if usuario_digitado in usuarios_validos and usuarios_validos[usuario_digitado] == senha_digitada:
                return True
    except: pass
    return False

if not st.session_state["autenticado"]:
    st.title("🔒 Hydro Manager - Acesso Restrito")
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

# ==========================================
# MOTOR DE BACKUP (EXPORTAR E IMPORTAR)
# ==========================================
def gerar_backup_projeto(db, projeto_id):
    proj = db.query(Projeto).filter(Projeto.id == projeto_id).first()
    if not proj: return ""
    
    dados = {
        "projeto": {
            "nome": proj.nome, "tipo": proj.tipo, "municipio_uf": proj.municipio_uf, 
            "rio": proj.rio, "potencia_mw": proj.potencia_mw, "concluido": getattr(proj, "concluido", False)
        },
        "fases": [], "tarefas": [], "subtarefas": [], "dependencias": [], "documentos": []
    }
    
    fases = db.query(Fase).filter(Fase.projeto_id == projeto_id).all()
    fase_ids = [f.id for f in fases]
    for f in fases:
        dados["fases"].append({"id_antigo": f.id, "nome": f.nome, "ordem": f.ordem})
        
    tarefas = db.query(Tarefa).filter(Tarefa.fase_id.in_(fase_ids)).all() if fase_ids else []
    tarefa_ids = [t.id for t in tarefas]
    for t in tarefas:
        dados["tarefas"].append({
            "id_antigo": t.id, "fase_id_antigo": t.fase_id, "nome": t.nome, "status": t.status, 
            "prioridade": t.prioridade, "responsavel": t.responsavel,
            "data_inicio": t.data_inicio.isoformat() if t.data_inicio else None,
            "data_termino": t.data_termino.isoformat() if t.data_termino else None,
            "percentual_concluido": t.percentual_concluido, "is_marco": t.is_marco
        })
        
    for s in (db.query(Subtarefa).filter(Subtarefa.tarefa_id.in_(tarefa_ids)).all() if tarefa_ids else []):
        dados["subtarefas"].append({"tarefa_id_antigo": s.tarefa_id, "nome": s.nome, "concluida": s.concluida})
        
    for d in (db.query(Dependencia).filter(Dependencia.tarefa_predecessora_id.in_(tarefa_ids)).all() if tarefa_ids else []):
        dados["dependencias"].append({"pred_id_antigo": d.tarefa_predecessora_id, "suc_id_antigo": d.tarefa_sucessora_id, "tipo": d.tipo})
        
    for doc in db.query(Documento).filter(Documento.projeto_id == projeto_id).all():
        dados["documentos"].append({"nome": doc.nome, "url": doc.url})
        
    return json.dumps(dados, indent=4)

def restaurar_projeto(db, json_string):
    try:
        dados = json.loads(json_string)
        p_data = dados["projeto"]
        novo_proj = Projeto(
            nome=p_data["nome"] + " (Restaurado)", tipo=p_data.get("tipo"), 
            municipio_uf=p_data.get("municipio_uf"), rio=p_data.get("rio"), 
            potencia_mw=p_data.get("potencia_mw"), concluido=p_data.get("concluido", False)
        )
        db.add(novo_proj)
        db.flush()
        
        mapa_fases = {}
        for f in dados.get("fases", []):
            nova_fase = Fase(projeto_id=novo_proj.id, nome=f["nome"], ordem=f["ordem"])
            db.add(nova_fase)
            db.flush()
            mapa_fases[f["id_antigo"]] = nova_fase.id
            
        mapa_tarefas = {}
        for t in dados.get("tarefas", []):
            dt_ini = datetime.date.fromisoformat(t["data_inicio"]) if t.get("data_inicio") else None
            dt_fim = datetime.date.fromisoformat(t["data_termino"]) if t.get("data_termino") else None
            nova_tar = Tarefa(
                fase_id=mapa_fases[t["fase_id_antigo"]], nome=t["nome"], status=t["status"],
                prioridade=t["prioridade"], responsavel=t["responsavel"], data_inicio=dt_ini,
                data_termino=dt_fim, percentual_concluido=t["percentual_concluido"], is_marco=t["is_marco"]
            )
            db.add(nova_tar)
            db.flush()
            mapa_tarefas[t["id_antigo"]] = nova_tar.id
            
        for s in dados.get("subtarefas", []):
            db.add(Subtarefa(tarefa_id=mapa_tarefas[s["tarefa_id_antigo"]], nome=s["nome"], concluida=s["concluida"]))
            
        for d in dados.get("dependencias", []):
            db.add(Dependencia(tarefa_predecessora_id=mapa_tarefas[d["pred_id_antigo"]], tarefa_sucessora_id=mapa_tarefas[d["suc_id_antigo"]], tipo=d.get("tipo", "Fim-Início")))
            
        for doc in dados.get("documentos", []):
            db.add(Documento(projeto_id=novo_proj.id, nome=doc["nome"], url=doc["url"]))
            
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False
# ==========================================

st.title("🌊 Hydro Manager")
st.write("Gestão de Projetos e Engenharia de Usinas Hidrelétricas")

col_add, col_import = st.columns(2)

with col_add.expander("➕ Novo Projeto", expanded=False):
    with st.form("form_novo_projeto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do Projeto *")
        tipo = c2.selectbox("Tipo *", ["UHE", "PCH", "CGH"])
        rio = c1.text_input("Rio")
        pot = c2.number_input("Potência (MW)", min_value=0.0, format="%.2f")
        
        # --- MENU DE TEMPLATES ATUALIZADO ---
        opcao_template = st.selectbox(
            "Carregar Estrutura Automática", 
            ["Projeto Básico (Com tarefas e capítulos)", "Outorga D'água", "Cronograma Padrão Completo", "Nenhum (Criar do zero)"]
        )
        
        if st.form_submit_button("Salvar Projeto", type="primary"):
            if not nome:
                st.error("O nome do projeto é obrigatório.")
            else:
                novo_proj = Projeto(nome=nome, tipo=tipo, rio=rio, potencia_mw=pot)
                db.add(novo_proj)
                db.commit()
                db.refresh(novo_proj)
                
                # Só roda o script se o usuário não escolheu "Nenhum"
                if opcao_template != "Nenhum (Criar do zero)":
                    from services.template_hydro import aplicar_template_hydro
                    aplicar_template_hydro(db, novo_proj.id, opcao_template)
                    
                st.success("Projeto criado!")
                st.rerun()

with col_import.expander("📥 Importar Projeto (.hydro)", expanded=False):
    st.write("Restaure um projeto salvo anteriormente.")
    arquivo_upload = st.file_uploader("Selecione o arquivo .hydro", type=["hydro"])
    if st.button("Restaurar Arquivo"):
        if arquivo_upload is not None:
            conteudo = arquivo_upload.read().decode("utf-8")
            if restaurar_projeto(db, conteudo):
                st.success("Projeto restaurado com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao ler o arquivo. Ele pode estar corrompido.")

st.divider()

# --- FUNÇÃO PARA RENDERIZAR OS CARTÕES DOS PROJETOS ---
def renderizar_projetos(lista_projetos, eh_concluido=False):
    if not lista_projetos:
        st.info("Nenhum projeto encontrado nesta aba.")
        return
        
    cols = st.columns(3)
    for i, proj in enumerate(lista_projetos):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {proj.nome}")
                st.write(f"**Tipo:** {proj.tipo} | **Potência:** {proj.potencia_mw} MW")
                st.write(f"📍 {proj.municipio_uf or 'Local não definido'}")
                
                tarefas_projeto = db.query(Tarefa).join(Fase).filter(Fase.projeto_id == proj.id).all()
                media_progresso = sum((100 if t.status == "Concluída" else (t.percentual_concluido or 0)) for t in tarefas_projeto) / len(tarefas_projeto) if tarefas_projeto else 0.0
                
                cor_barra = "green" if eh_concluido else "blue"
                st.progress(100 if eh_concluido else int(media_progresso), text=f"Progresso Geral: {100 if eh_concluido else int(media_progresso)}%") 
                
                with st.expander("✏️ Editar Projeto"):
                    with st.form(f"form_edit_proj_{proj.id}", clear_on_submit=False):
                        edit_nome = st.text_input("Nome", value=proj.nome)
                        opcoes_tipo = ["UHE", "PCH", "CGH"]
                        edit_tipo = st.selectbox("Tipo", opcoes_tipo, index=opcoes_tipo.index(proj.tipo) if proj.tipo in opcoes_tipo else 0)
                        edit_local = st.text_input("Local", value=proj.municipio_uf or "")
                        edit_rio = st.text_input("Rio", value=proj.rio or "")
                        edit_pot = st.number_input("Potência (MW)", min_value=0.0, format="%.2f", value=float(proj.potencia_mw or 0.0))
                        
                        if st.form_submit_button("Salvar Alterações"):
                            if edit_nome:
                                proj.nome, proj.tipo, proj.municipio_uf, proj.rio, proj.potencia_mw = edit_nome, edit_tipo, edit_local, edit_rio, edit_pot
                                db.commit()
                                st.rerun()
                
                with st.expander("📂 Documentos e Links"):
                    for d in db.query(Documento).filter(Documento.projeto_id == proj.id).all():
                        c_link, c_del = st.columns([0.8, 0.2])
                        c_link.markdown(f"🔗 [{d.nome}]({d.url})")
                        if c_del.button("🗑️", key=f"del_doc_{d.id}"):
                            db.delete(d)
                            db.commit()
                            st.rerun()
                    with st.form(f"form_doc_{proj.id}", clear_on_submit=True):
                        doc_nome = st.text_input("Nome (Ex: Planta)", key=f"nome_doc_{proj.id}")
                        doc_url = st.text_input("Link", key=f"url_doc_{proj.id}")
                        if st.form_submit_button("Salvar Link") and doc_nome and doc_url:
                            db.add(Documento(projeto_id=proj.id, nome=doc_nome, url=doc_url))
                            db.commit()
                            st.rerun()

                # --- BOTÕES DE AÇÃO: 4 COLUNAS APERTADINHAS PARA CABER TUDO ---
                c_painel, c_arq, c_down, c_del = st.columns([1.2, 1.2, 1, 1])
                
                if c_painel.button("Abrir", key=f"abrir_{proj.id}", use_container_width=True):
                    st.session_state['projeto_ativo_id'] = proj.id
                    st.switch_page("pages/1_Painel_de_Tarefas.py")
                    
                # Botão Dinâmico: Finalizar ou Reabrir
                txt_botao = "Reabrir" if eh_concluido else "Finalizar"
                icone = "🔄" if eh_concluido else "✅"
                if c_arq.button(f"{icone} {txt_botao}", key=f"arq_{proj.id}", use_container_width=True):
                    proj.concluido = not proj.concluido
                    db.commit()
                    st.rerun()
                    
                # BOTÃO DE DOWNLOAD DO BACKUP
                json_backup = gerar_backup_projeto(db, proj.id)
                c_down.download_button(
                    label="⬇️ Salvar",
                    data=json_backup,
                    file_name=f"{proj.nome.replace(' ', '_')}.hydro",
                    mime="application/json",
                    use_container_width=True
                )
                
                if c_del.button("Excluir", key=f"del_{proj.id}", use_container_width=True):
                    db.delete(proj)
                    db.commit()
                    st.rerun()

# --- BUSCA E DIVISÃO EM ABAS ---
projetos_ativos = db.query(Projeto).filter(Projeto.concluido == False).all()
projetos_concluidos = db.query(Projeto).filter(Projeto.concluido == True).all()

aba_ativos, aba_concluidos = st.tabs(["🏗️ Projetos Ativos", "✅ Projetos Concluídos"])

with aba_ativos:
    renderizar_projetos(projetos_ativos, eh_concluido=False)

with aba_concluidos:
    renderizar_projetos(projetos_concluidos, eh_concluido=True)
