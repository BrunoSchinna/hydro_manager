from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Responsavel(Base):
    __tablename__ = "responsaveis"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    
    tarefas = relationship("Tarefa", back_populates="responsavel")

class Projeto(Base):
    __tablename__ = "projetos"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    tipo = Column(String(50), nullable=False) # UHE, PCH, CGH
    rio = Column(String(100))
    municipio_uf = Column(String(100))
    potencia_mw = Column(Float)
    responsavel_id = Column(Integer, ForeignKey("responsaveis.id"))
    data_inicio = Column(Date, default=datetime.date.today)
    data_termino_prevista = Column(Date)
    status = Column(String(50), default="Em planejamento") # Planejamento, Em andamento, Paralisado, Concluído
    descricao = Column(Text)
    
    fases = relationship("Fase", back_populates="projeto", cascade="all, delete-orphan")

class Fase(Base):
    __tablename__ = "fases"
    
    id = Column(Integer, primary_key=True, index=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(150), nullable=False)
    ordem = Column(Integer, default=0) # Para manter a ordem (ex: 1. Viabilidade, 2. Básico)
    cor = Column(String(20), default="#3498db") # Cor da tag da fase
    
    projeto = relationship("Projeto", back_populates="fases")
    tarefas = relationship("Tarefa", back_populates="fase", cascade="all, delete-orphan")

class Tarefa(Base):
    __tablename__ = "tarefas"
    
    id = Column(Integer, primary_key=True, index=True)
    fase_id = Column(Integer, ForeignKey("fases.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(200), nullable=False)
    responsavel_id = Column(Integer, ForeignKey("responsaveis.id"), nullable=True)
    
    status = Column(String(50), default="Não iniciada") # Não iniciada, Em andamento, Travada, Concluída
    prioridade = Column(String(50), default="Média") # Baixa, Média, Alta, Crítica
    
    data_inicio = Column(Date)
    data_termino = Column(Date)
    duracao_dias = Column(Integer, default=1)
    percentual_concluido = Column(Float, default=0.0)
    
    observacoes = Column(Text)
    is_marco = Column(Boolean, default=False) # Milestone (Duração 0)
    
    fase = relationship("Fase", back_populates="tarefas")
    responsavel = relationship("Responsavel", back_populates="tarefas")
    
    # Relações para lidar com as dependências (predecessoras e sucessoras)
    predecessoras = relationship(
        "Dependencia",
        foreign_keys="[Dependencia.tarefa_sucessora_id]",
        back_populates="sucessora",
        cascade="all, delete-orphan"
    )
    sucessoras = relationship(
        "Dependencia",
        foreign_keys="[Dependencia.tarefa_predecessora_id]",
        back_populates="predecessora",
        cascade="all, delete-orphan"
    )

class Dependencia(Base):
    __tablename__ = "dependencias"
    
    id = Column(Integer, primary_key=True, index=True)
    tarefa_predecessora_id = Column(Integer, ForeignKey("tarefas.id", ondelete="CASCADE"), nullable=False)
    tarefa_sucessora_id = Column(Integer, ForeignKey("tarefas.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), default="Fim-Início") # Fim-Início, Início-Início, etc.
    
    predecessora = relationship("Tarefa", foreign_keys=[tarefa_predecessora_id], back_populates="sucessoras")
    sucessora = relationship("Tarefa", foreign_keys=[tarefa_sucessora_id], back_populates="predecessoras")
