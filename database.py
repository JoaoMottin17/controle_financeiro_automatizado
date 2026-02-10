from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
import socket

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
    centro_custo = Column(String(100))
    categoria_ia = Column(String(50))
    confianca_ia = Column(Float)
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
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
    if not db_url:
        if not os.path.exists('data'):
            os.makedirs('data')
        db_url = 'sqlite:///data/database.db'

    # Ajustar URL para Postgres se necessário
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    connect_args = {}
    if "postgresql+psycopg2://" in db_url:
        # Forçar SSL no Postgres se não estiver definido
        if "sslmode=" not in db_url:
            sep = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{sep}sslmode=require"

        # Resolver IPv4 para evitar erro "Cannot assign requested address" (IPv6)
        try:
            url = make_url(db_url)
            if url.host:
                # Resolver apenas IPv4
                ipv4 = socket.getaddrinfo(url.host, None, socket.AF_INET)[0][4][0]
                # Substituir host por IPv4 diretamente na URL e forçar host no connect_args
                db_url = url.set(host=ipv4).render_as_string(hide_password=False)
                connect_args["host"] = ipv4
                connect_args["hostaddr"] = ipv4
        except Exception:
            pass

    # Usar NullPool com Supabase Transaction Pooler (porta 6543)
    poolclass = None
    try:
        url_check = make_url(db_url)
        if str(url_check.port) == "6543" or (url_check.host and "pooler.supabase.com" in url_check.host):
            poolclass = NullPool
    except Exception:
        pass

    if poolclass:
        engine = create_engine(db_url, connect_args=connect_args, poolclass=poolclass)
    else:
        engine = create_engine(db_url, connect_args=connect_args)
    Base.metadata.create_all(engine)

    # Migrações simples (SQLite e Postgres)
    try:
        if db_url.startswith("sqlite:///"):
            with engine.connect() as conn:
                result = conn.execute("PRAGMA table_info(transacoes)")
                colunas = [row[1] for row in result.fetchall()]
                if 'centro_custo' not in colunas:
                    conn.execute("ALTER TABLE transacoes ADD COLUMN centro_custo VARCHAR(100)")
                if 'confianca_ia' not in colunas:
                    conn.execute("ALTER TABLE transacoes ADD COLUMN confianca_ia FLOAT")
        else:
            from sqlalchemy import text
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS centro_custo VARCHAR(100)"))
                conn.execute(text("ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS confianca_ia FLOAT"))
    except Exception as e:
        print(f"Erro ao aplicar migração simples: {e}")
    
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
