import streamlit as st
import bcrypt
import datetime
from database import get_session, Usuario, ConfigSistema

# Inicialização da sessão
def init_session():
    """Inicializa variáveis de sessão"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False

# Funções de hash e verificação de senha
def hash_password(password):
    """Hash da senha usando bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    """Verifica se a senha corresponde ao hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# Função para criar admin padrão
def criar_admin_padrao():
    """Cria usuário admin padrão se não existir"""
    session = get_session()
    try:
        admin = session.query(Usuario).filter_by(username='admin').first()
        if not admin:
            hashed_pw = hash_password('admin123')
            admin = Usuario(
                username='admin',
                password_hash=hashed_pw,
                email='admin@sistema.com',
                nivel_acesso='admin',
                ativo=True
            )
            session.add(admin)
            session.commit()
            print("✅ Admin padrão criado: admin / admin123")
    except Exception as e:
        session.rollback()
        print(f"Erro ao criar admin: {e}")
    finally:
        session.close()

# Função de autenticação CORRIGIDA
def autenticar_usuario(username, password):
    """Autentica um usuário"""
    session = get_session()
    try:
        user = session.query(Usuario).filter_by(username=username, ativo=True).first()
        if user and verify_password(password, user.password_hash):
            # Atualizar último login
            user.ultimo_login = datetime.datetime.utcnow()
            session.commit()
            
            # Salvar os dados do usuário ANTES de fechar a sessão
            user_data = {
                'id': user.id,
                'username': user.username,
                'nivel_acesso': user.nivel_acesso,
                'email': user.email
            }
            
            return True, user_data
        return False, None
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return False, None
    finally:
        session.close()

# Funções para verificação de estado
def check_auth():
    """Verifica se o usuário está autenticado"""
    init_session()
    return st.session_state.logged_in

def is_admin():
    """Verifica se o usuário é administrador"""
    init_session()
    return st.session_state.get('is_admin', False)

# Página de login CORRIGIDA
def login_page():
    """Renderiza a página de login"""
    init_session()
    criar_admin_padrao()
    
    st.title("💰 Sistema de Análise Financeira Pessoal")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.subheader("🔐 Login de Acesso")
            
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("Usuário", placeholder="Digite seu usuário")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                submit = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Por favor, preencha todos os campos")
                    else:
                        success, user_data = autenticar_usuario(username, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_data['id']
                            st.session_state.username = user_data['username']
                            st.session_state.is_admin = (user_data['nivel_acesso'] == 'admin')
                            st.success(f"✅ Bem-vindo, {user_data['username']}!")
                            
                            # Registrar login no sistema
                            session = get_session()
                            try:
                                config = ConfigSistema(
                                    chave=f'LOGIN_{user_data["username"]}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}',
                                    valor='SUCESSO',
                                    descricao=f'Login realizado por {user_data["username"]}'
                                )
                                session.add(config)
                                session.commit()
                            except Exception as e:
                                print(f"Erro ao registrar login: {e}")
                            finally:
                                session.close()
                            
                            st.rerun()
                        else:
                            st.error("❌ Usuário ou senha incorretos")
            
            st.markdown("---")
            st.caption("💡 **Credenciais padrão (admin):**")
            st.caption("👤 Usuário: admin")
            st.caption("🔑 Senha: admin123")
            st.caption("*Altere a senha após o primeiro login*")
            
            st.markdown("---")
            st.info("""
            **Acesso Restrito:**
            - Novos usuários devem ser cadastrados por um administrador
            - Contate o administrador do sistema para criar sua conta
            """)

# Exportar funções
__all__ = ['login_page', 'check_auth', 'is_admin', 'hash_password', 'verify_password', 'autenticar_usuario']