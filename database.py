from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    email = Column(String(100))
    nivel_acesso = Column(String(20), default='usuario')
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    ultimo_login = Column(DateTime)

class Transacao(Base):
    __tablename__ = 'transacoes'
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=False)
    data = Column(DateTime, nullable=False)
    descricao = Column(String(200))
    valor = Column(Float, nullable=False)
    tipo = Column(String(20))
    banco = Column(String(50))
    categoria_ia = Column(String(50))
    categoria_manual = Column(String(50))
    tags = Column(String(200))
    parcelamento = Column(Boolean, default=False)
    parcela_atual = Column(Integer)
    parcela_total = Column(Integer)
    data_vencimento = Column(DateTime)
    processado = Column(Boolean, default=False)

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer)
    nome = Column(String(50))
    palavras_chave = Column(Text)
    tipo = Column(String(20))

class ConfigSistema(Base):  # ADICIONE ESTA CLASSE
    __tablename__ = 'config_sistema'
    id = Column(Integer, primary_key=True)
    chave = Column(String(50), unique=True)
    valor = Column(Text)
    descricao = Column(String(200))

def init_db():
    """Inicializa o banco de dados"""
    if not os.path.exists('data'):
        os.makedirs('data')
    
    engine = create_engine('sqlite:///data/database.db')
    Base.metadata.create_all(engine)
    
    # Criar configurações padrão
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Verifica se já existem configurações
        configs = session.query(ConfigSistema).first()
        if not configs:
            configuracoes_padrao = [
                ConfigSistema(
                    chave='SISTEMA_ATIVO', 
                    valor='true', 
                    descricao='Sistema ativo'
                ),
                ConfigSistema(
                    chave='MAX_UPLOAD_MB', 
                    valor='10', 
                    descricao='Tamanho máximo upload (MB)'
                ),
                ConfigSistema(
                    chave='BACKUP_AUTOMATICO', 
                    valor='false', 
                    descricao='Backup automático'
                ),
            ]
            for config in configuracoes_padrao:
                session.add(config)
            session.commit()
    except Exception as e:
        print(f"Erro ao criar configurações padrão: {e}")
        session.rollback()
    finally:
        session.close()
    
    return engine

def get_session():
    """Retorna uma sessão do banco de dados"""
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()