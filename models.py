from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Projeto(Base):
    __tablename__ = "projetos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String)  # UHE, PCH, CGH
    municipio_uf = Column(String)
    rio = Column(String)
    potencia_mw = Column(Float)
    
    fases = relationship("Fase", back_populates="projeto", cascade="all, delete-orphan")

class Fase(Base):
    __tablename__ = "fases"
    id = Column(Integer, primary_key=True, index=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id", ondelete="CASCADE"))
    nome = Column(String, nullable=False)
    ordem = Column(Integer)
    
    projeto = relationship("Projeto", back_populates="fases")
    tarefas = relationship("Tarefa", back_populates="fase", cascade="all, delete-orphan")

class Tarefa(Base):
    __tablename__ = "tarefas"
    id = Column(Integer, primary_key=True, index=True)
    fase_id = Column(Integer, ForeignKey("fases.id", ondelete="CASCADE"))
    nome = Column(String, nullable=False)
    descricao = Column(String)
    status = Column(String, default="Não iniciada")
    prioridade = Column(String, default="Média")
    data_inicio = Column(Date)
    data_termino = Column(Date)
    percentual_concluido = Column(Float, default=0.0)
    is_marco = Column(Boolean, default=False)
    
    fase = relationship("Fase", back_populates="tarefas")
    # Ligação com as novas subtarefas (se a tarefa for apagada, as subtarefas dela somem também)
    subtarefas = relationship("Subtarefa", back_populates="tarefa", cascade="all, delete-orphan")

# --- NOVA TABELA: SUBTAREFAS ---
class Subtarefa(Base):
    __tablename__ = "subtarefas"
    id = Column(Integer, primary_key=True, index=True)
    tarefa_id = Column(Integer, ForeignKey("tarefas.id", ondelete="CASCADE"))
    nome = Column(String, nullable=False)
    concluida = Column(Boolean, default=False)
    
    tarefa = relationship("Tarefa", back_populates="subtarefas")

class Responsavel(Base):
    __tablename__ = "responsaveis"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
