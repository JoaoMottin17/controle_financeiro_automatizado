import streamlit as st
import pandas as pd
from datetime import datetime
import warnings
import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

warnings.filterwarnings('ignore')

# Importar módulos - ADICIONE get_session AQUI!
try:
    from auth import login_page, check_auth, is_admin
    from csv_processor import processar_csv, salvar_transacoes
    from ai_classifier import ClassificadorFinanceiro
    from dashboard import carregar_dados, criar_dashboard
    from export import exportar_para_excel, exportar_para_csv, exportar_relatorio_completo
    from admin import gerenciar_usuarios, gerenciar_categorias, configurar_sistema, backup_dados
    from database import get_session, Usuario, Transacao, Categoria, ConfigSistema  # get_session JÁ ESTÁ AQUI, mas vamos garantir
except ImportError as e:
    st.error(f"Erro ao importar módulos: {e}")
    st.info("Certifique-se de que todos os arquivos estão no mesmo diretório:")
    st.code("""
    financas_pessoais/
    ├── app.py
    ├── auth.py
    ├── database.py
    ├── csv_processor.py
    ├── ai_classifier.py
    ├── dashboard.py
    ├── export.py
    └── admin.py
    """)
    st.stop()

# Configurar página
st.set_page_config(
    page_title="Sistema Financeiro Pessoal",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar classificador
@st.cache_resource
def get_classifier():
    classifier = ClassificadorFinanceiro()
    return classifier

def _get_config(chave, default=None):
    session = get_session()
    try:
        cfg = session.query(ConfigSistema).filter_by(chave=chave).first()
        return cfg.valor if cfg else default
    finally:
        session.close()

def _set_config(chave, valor, descricao=None):
    session = get_session()
    try:
        cfg = session.query(ConfigSistema).filter_by(chave=chave).first()
        if cfg:
            cfg.valor = str(valor)
            if descricao:
                cfg.descricao = descricao
        else:
            cfg = ConfigSistema(chave=chave, valor=str(valor), descricao=descricao or "")
            session.add(cfg)
        session.commit()
    finally:
        session.close()

def _clear_cached_data():
    try:
        st.cache_data.clear()
    except Exception:
        pass

# Verificar autenticação
if not check_auth():
    login_page()
    st.stop()

# Menu principal
st.sidebar.title(f"👤 {st.session_state['username']}")

if st.session_state.get('is_admin', False):
    menu_options = [
        "📤 Importar CSV", 
        "📊 Dashboard", 
        "🏷️ Classificar Manualmente", 
        "📥 Exportar", 
        "⚙️ Configurações"
    ]
else:
    menu_options = [
        "📤 Importar CSV", 
        "📊 Dashboard", 
        "🏷️ Classificar Manualmente", 
        "📥 Exportar"
    ]

menu = st.sidebar.selectbox("Menu", menu_options)

# Página: Importar CSV
if menu == "📤 Importar CSV":
    st.title("📤 Importar Arquivos CSV")
    
    st.info("""
    **Instruções:**
    1. Exporte seus extratos bancários no formato CSV
    2. Selecione os arquivos abaixo
    3. Escolha o banco correspondente
    4. Clique em Processar Arquivos
    """)
    
    uploaded_files = st.file_uploader(
        "Selecione arquivos CSV",
        type=['csv'],
        accept_multiple_files=True,
        help="Formato aceito: .csv"
    )
    
    # ==============================================
    # PARTE MODIFICADA: SELEÇÃO DE BANCOS (OPÇÃO 2)
    # ==============================================
    
    # Bancos predefinidos (lista mais completa)
    bancos_predefinidos = [
        "Itaú", "Bradesco", "Santander", "Nubank", "Inter", "Caixa", 
        "Banco do Brasil", "Banrisul", "Sicoob", "Sicredi", "Original",
        "Next", "C6 Bank", "BTG Pactual", "Rico", "XP Investimentos",
        "Modal Mais", "Warren", "Mercado Pago", "PicPay", "Neon",
        "PagBank", "BS2", "Banco Pan", "Banco Sofisa", "Banco Rendimento",
        "Banco Daycoval", "Banco Pine", "Banco ABC Brasil", "Banco Votorantim",
        "Banco Safra", "Banco do Nordeste", "Banestes", "BRB", "BANPARÁ",
        "Outro (especificar abaixo)"
    ]
    
    # Seleção do banco
    banco_selecionado = st.selectbox(
        "Selecione o banco",
        bancos_predefinidos,
        help="Se não encontrar seu banco, selecione 'Outro' e digite o nome abaixo"
    )
    
    # Se selecionou "Outro", mostrar campo para digitar
    if banco_selecionado == "Outro (especificar abaixo)":
        novo_banco = st.text_input(
            "Digite o nome do seu banco:",
            placeholder="Ex: Banco da Minha Empresa, Cooperativa XYZ..."
        )
        
        if novo_banco:
            banco_nome = novo_banco
        else:
            banco_nome = "Outro"
            st.warning("Por favor, digite o nome do banco")
    else:
        banco_nome = banco_selecionado
    
    # Sugestão de bancos recentes (se houver)
    if 'bancos_recentes' in st.session_state and st.session_state.bancos_recentes:
        st.write("**Bancos usados recentemente:**")
        cols = st.columns(4)
        for idx, banco in enumerate(st.session_state.bancos_recentes[:4]):
            with cols[idx % 4]:
                if st.button(f"🏦 {banco}", key=f"banco_rapido_{idx}"):
                    banco_nome = banco
                    st.success(f"Banco '{banco}' selecionado!")
    
    # ==============================================
    # FIM DA PARTE MODIFICADA
    # ==============================================
    
    # Opção de processamento automático
    auto_classificar = st.checkbox("Classificar transações automaticamente com IA (OpenAI)", value=True)
    openai_model = _get_config("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-5"))
    openai_batch = int(_get_config("OPENAI_BATCH", 20))
    openai_temp = float(_get_config("OPENAI_TEMP", 0.0))
    if auto_classificar:
        if os.getenv("OPENAI_API_KEY"):
            with st.expander("⚙️ Configurações OpenAI", expanded=False):
                openai_model = st.text_input("Modelo", value=str(openai_model))
                openai_batch = st.number_input("Tamanho do lote", min_value=1, max_value=100, value=int(openai_batch), step=1)
                openai_temp = st.slider("Temperatura", min_value=0.0, max_value=1.0, value=float(openai_temp), step=0.1)

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Salvar configurações", use_container_width=True):
                        _set_config("OPENAI_MODEL", openai_model, "Modelo OpenAI")
                        _set_config("OPENAI_BATCH", int(openai_batch), "Tamanho do lote OpenAI")
                        _set_config("OPENAI_TEMP", float(openai_temp), "Temperatura OpenAI")
                        st.success("Configurações salvas!")
                with col_b:
                    if st.button("✅ Validar modelo", use_container_width=True):
                        try:
                            client = get_classifier()._get_openai_client()
                            if client is None:
                                st.error("OPENAI_API_KEY não configurada.")
                            else:
                                resp = client.responses.create(
                                    model=openai_model,
                                    input="Responda apenas com a palavra OK."
                                )
                                text = getattr(resp, "output_text", "")
                                if "OK" in text:
                                    st.success("Modelo validado com sucesso.")
                                else:
                                    st.warning("Modelo respondeu, mas sem OK. Verifique o modelo.")
                        except Exception as e:
                            st.error(f"Falha ao validar modelo: {e}")
        else:
            st.error("OPENAI_API_KEY não configurada nos Secrets do Streamlit.")
            auto_classificar = False
    
    if uploaded_files and st.button("Processar Arquivos", type="primary"):
        classifier = get_classifier()
        total_transacoes = 0
        total_salvas = 0
        total_duplicadas = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                status_text.text(f"Processando: {uploaded_file.name}...")
                
                # Salvar banco nos recentes
                if banco_nome and banco_nome != "Outro (especificar abaixo)":
                    if 'bancos_recentes' not in st.session_state:
                        st.session_state.bancos_recentes = []
                    
                    # Adicionar/atualizar lista de bancos recentes
                    if banco_nome in st.session_state.bancos_recentes:
                        # Se já existe, move para o início
                        st.session_state.bancos_recentes.remove(banco_nome)
                    
                    st.session_state.bancos_recentes.insert(0, banco_nome)
                    
                    # Manter apenas os 5 mais recentes
                    if len(st.session_state.bancos_recentes) > 5:
                        st.session_state.bancos_recentes = st.session_state.bancos_recentes[:5]
                
                # Processar CSV
                df_transacoes = processar_csv(
                    uploaded_file, 
                    st.session_state['user_id'], 
                    banco_nome
                )
                
                if df_transacoes.empty:
                    st.warning(f"Nenhuma transação encontrada em {uploaded_file.name}")
                    continue
                
                # Classificar com IA se solicitado
                if auto_classificar:
                    df_transacoes = classifier.classificar_transacoes_api(
                        df_transacoes,
                        batch_size=int(openai_batch),
                        model=openai_model,
                        temperature=float(openai_temp)
                    )
                else:
                    df_transacoes['categoria_ia'] = None
                
                # Salvar no banco de dados
                resultado = salvar_transacoes(df_transacoes)
                
                if resultado:
                    st.success(f"✅ {uploaded_file.name} processado! {resultado['salvas']} transações salvas, {resultado['duplicadas']} duplicadas ignoradas.")
                    
                    total_transacoes += resultado['total']
                    total_salvas += resultado['salvas']
                    total_duplicadas += resultado['duplicadas']
                    _clear_cached_data()
                    
                    # Mostrar preview
                    with st.expander(f"Visualizar transações de {uploaded_file.name}"):
                        st.dataframe(
                            df_transacoes[['data', 'descricao', 'valor', 'tipo', 'centro_custo', 'categoria_ia']].head(10),
                            use_container_width=True
                        )
                
                progress_bar.progress((i + 1) / len(uploaded_files))
                
            except Exception as e:
                st.error(f"❌ Erro ao processar {uploaded_file.name}: {str(e)}")
        
        if total_transacoes > 0:
            st.success(f"""
            🎉 **Processamento completo!**
            
            **Resumo:**
            - 📄 Arquivos processados: {len(uploaded_files)}
            - 💰 Transações encontradas: {total_transacoes}
            - 💾 Transações salvas: {total_salvas}
            - 🔄 Duplicadas ignoradas: {total_duplicadas}
            """)
            
            # Salvar modelo se houve novas classificações
            if auto_classificar and total_salvas > 0:
                classifier.salvar_modelo()

# Página: Dashboard
elif menu == "📊 Dashboard":
    st.title("📊 Dashboard Financeiro")
    
    # Carregar dados
    periodo = st.sidebar.slider(
        "Período (meses)", 
        min_value=1, 
        max_value=24, 
        value=12,
        help="Selecione o número de meses para análise"
    )
    
    df = carregar_dados(st.session_state['user_id'], periodo)
    
    if df.empty:
        st.warning("Nenhuma transação encontrada. Importe arquivos CSV primeiro.")
        if st.button("Ir para Importar CSV"):
            st.rerun()
    else:
        # Criar dashboard
        df_filtrado = criar_dashboard(df, st.session_state['user_id'])
        
        # Mostrar tabela com dados filtrados
        with st.expander("📋 Visualizar Dados Detalhados", expanded=False):
            st.dataframe(
                df_filtrado.sort_values('Data', ascending=False),
                use_container_width=True,
                height=400
            )

# Página: Classificar Manualmente
elif menu == "🏷️ Classificar Manualmente":
    st.title("🏷️ Classificação Manual de Transações")
    
    # USAR get_session() AQUI - IMPORTADO DO DATABASE
    session = get_session()
    try:
        # Buscar transações não classificadas manualmente
        transacoes = session.query(Transacao).filter(
            Transacao.usuario_id == st.session_state['user_id'],
            Transacao.categoria_manual.is_(None)
        ).order_by(Transacao.data.desc()).limit(50).all()
        
        if not transacoes:
            st.info("🎉 Todas as transações já foram classificadas manualmente!")
            st.info("Para classificar mais transações, importe novos arquivos CSV.")
        else:
            st.info(f"📝 {len(transacoes)} transações aguardando classificação")
            
            # Buscar categorias existentes do usuário
            categorias_usuario = session.query(Categoria).filter(
                Categoria.usuario_id == st.session_state['user_id']
            ).all()
            
            # Lista de categorias
            categorias_padrao = [
                'ALIMENTACAO', 'TRANSPORTE', 'MORADIA', 'SAUDE', 
                'EDUCACAO', 'LAZER', 'VESTUARIO', 'SERVICOS',
                'SALARIO', 'TRANSFERENCIA', 'INVESTIMENTO', 'OUTROS'
            ]
            
            # Adicionar categorias personalizadas
            categorias_personalizadas = [cat.nome for cat in categorias_usuario]
            todas_categorias = list(set(categorias_padrao + categorias_personalizadas))
            todas_categorias.sort()
            
            for i, transacao in enumerate(transacoes):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{transacao.descricao}**")
                        st.caption(f"{transacao.data.strftime('%d/%m/%Y')} | {transacao.banco}")
                    
                    with col2:
                        cor = "green" if transacao.valor > 0 else "red"
                        st.markdown(f"<span style='color:{cor};font-weight:bold'>R$ {abs(transacao.valor):,.2f}</span>", 
                                   unsafe_allow_html=True)
                    
                    with col3:
                        st.text(transacao.tipo)
                    
                    with col4:
                        categoria_atual = transacao.categoria_ia or 'OUTROS'
                        nova_categoria = st.selectbox(
                            "Categoria",
                            options=todas_categorias,
                            index=todas_categorias.index(categoria_atual) if categoria_atual in todas_categorias else len(todas_categorias)-1,
                            key=f"cat_{transacao.id}",
                            label_visibility="collapsed"
                        )
                    
                    with col5:
                        if st.button("💾", key=f"btn_{transacao.id}", help="Salvar categoria"):
                            transacao.categoria_manual = nova_categoria
                            session.commit()
                            st.success(f"Categoria salva: {nova_categoria}")
                            st.rerun()
                
                if i < len(transacoes) - 1:
                    st.divider()
        
        # Mostrar estatísticas
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Estatísticas")
        
        total_transacoes = session.query(Transacao).filter_by(
            usuario_id=st.session_state['user_id']
        ).count()
        
        classificadas_manual = session.query(Transacao).filter(
            Transacao.usuario_id == st.session_state['user_id'],
            Transacao.categoria_manual.isnot(None)
        ).count()
        
        classificadas_ia = session.query(Transacao).filter(
            Transacao.usuario_id == st.session_state['user_id'],
            Transacao.categoria_ia.isnot(None),
            Transacao.categoria_manual.is_(None)
        ).count()
        
        st.sidebar.metric("Total Transações", total_transacoes)
        st.sidebar.metric("Classificadas Manual", classificadas_manual)
        st.sidebar.metric("Classificadas por IA", classificadas_ia)
        
        if total_transacoes > 0:
            porcentagem = (classificadas_manual / total_transacoes) * 100
            st.sidebar.progress(int(porcentagem), text=f"Classificação: {porcentagem:.1f}%")
        
    finally:
        session.close()

# Página: Exportar
elif menu == "📥 Exportar":
    st.title("📥 Exportar Dados")
    
    st.info("Exporte seus dados financeiros para análise externa ou backup.")
    
    tab1, tab2, tab3 = st.tabs(["Excel", "CSV", "JSON"])
    
    with tab1:
        st.subheader("📊 Exportar para Excel")
        st.write("Exporte todos os seus dados em um arquivo Excel formatado com múltiplas planilhas.")
        
        if st.button("Gerar Relatório Excel Completo", use_container_width=True, type="primary"):
            with st.spinner("Gerando arquivo Excel..."):
                excel_file = exportar_para_excel(st.session_state['user_id'])
                
                if excel_file:
                    st.download_button(
                        label="⬇️ Baixar Arquivo Excel",
                        data=excel_file,
                        file_name=f"extrato_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        icon="📊"
                    )
                    
                    st.success("✅ Arquivo Excel gerado com sucesso!")
                    st.info("O arquivo contém 3 planilhas:\n1. Transações detalhadas\n2. Resumo por categoria\n3. Análise mensal")
                else:
                    st.error("❌ Nenhum dado disponível para exportar")
    
    with tab2:
        st.subheader("📋 Exportar para CSV")
        st.write("Exporte dados em formato CSV simples para importação em outros sistemas.")
        
        if st.button("Gerar Arquivo CSV", use_container_width=True, type="primary"):
            with st.spinner("Gerando arquivo CSV..."):
                csv_data = exportar_para_csv(st.session_state['user_id'])
                
                if csv_data:
                    st.download_button(
                        label="⬇️ Baixar Arquivo CSV",
                        data=csv_data,
                        file_name=f"transacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        icon="📋"
                    )
                    
                    st.success("✅ Arquivo CSV gerado com sucesso!")
                else:
                    st.error("❌ Nenhum dado disponível para exportar")
    
    with tab3:
        st.subheader("📄 Exportar para JSON")
        st.write("Exporte dados em formato JSON estruturado para análise programática.")
        
        if st.button("Gerar Relatório JSON", use_container_width=True, type="primary"):
            with st.spinner("Gerando arquivo JSON..."):
                json_data = exportar_relatorio_completo(st.session_state['user_id'])
                
                if json_data:
                    st.download_button(
                        label="⬇️ Baixar Arquivo JSON",
                        data=json_data,
                        file_name=f"relatorio_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True,
                        icon="📄"
                    )
                    
                    st.success("✅ Arquivo JSON gerado com sucesso!")
                    st.info("O JSON contém metadados, transações, categorias e resumo.")
                else:
                    st.error("❌ Nenhum dado disponível para exportar")
    
    # Estatísticas
    st.markdown("---")
    st.subheader("📈 Estatísticas do Banco de Dados")
    
    try:
        # USAR get_session() AQUI - IMPORTADO DO DATABASE
        session = get_session()
        
        total_transacoes = session.query(Transacao).filter_by(
            usuario_id=st.session_state['user_id']
        ).count()
        
        transacoes_classificadas = session.query(Transacao).filter(
            Transacao.usuario_id == st.session_state['user_id'],
            Transacao.categoria_manual.isnot(None)
        ).count()
        
        transacoes_ia = session.query(Transacao).filter(
            Transacao.usuario_id == st.session_state['user_id'],
            Transacao.categoria_ia.isnot(None)
        ).count()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Transações", total_transacoes)
        with col2:
            st.metric("Classificadas Manual", transacoes_classificadas)
        with col3:
            st.metric("Classificadas por IA", transacoes_ia)
        with col4:
            if total_transacoes > 0:
                porcentagem = (transacoes_classificadas / total_transacoes * 100)
                st.metric("Taxa Classificação", f"{porcentagem:.1f}%")
            else:
                st.metric("Taxa Classificação", "0%")
        
        session.close()
    except Exception as e:
        st.error(f"Erro ao calcular estatísticas: {e}")

# Página: Configurações (apenas para admin)
elif menu == "⚙️ Configurações":
    if not is_admin():
        st.warning("⚠️ Acesso restrito a administradores")
        st.info("Apenas usuários com perfil de administrador podem acessar esta página.")
    else:
        st.title("⚙️ Configurações do Sistema")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "👥 Usuários", 
            "🏷️ Categorias", 
            "⚙️ Sistema", 
            "💾 Backup", 
            "👤 Minha Conta"
        ])
        
        with tab1:
            gerenciar_usuarios()
        
        with tab2:
            gerenciar_categorias()
        
        with tab3:
            configurar_sistema()
        
        with tab4:
            backup_dados()
        
        with tab5:
            # Configurações da conta pessoal do admin
            st.subheader("👤 Minha Conta")
            
            # USAR get_session() AQUI - IMPORTADO DO DATABASE
            session = get_session()
            try:
                usuario = session.query(Usuario).filter_by(id=st.session_state.user_id).first()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**Usuário:** {usuario.username}")
                    st.info(f"**Email:** {usuario.email or 'Não cadastrado'}")
                    st.info(f"**Nível:** {usuario.nivel_acesso}")
                    st.info(f"**Status:** {'✅ Ativo' if usuario.ativo else '❌ Inativo'}")
                    st.info(f"**Conta criada em:** {usuario.created_at.strftime('%d/%m/%Y')}")
                    if usuario.ultimo_login:
                        st.info(f"**Último login:** {usuario.ultimo_login.strftime('%d/%m/%Y %H:%M')}")
                
                with col2:
                    with st.form("form_alterar_senha"):
                        st.write("### 🔐 Alterar Senha")
                        
                        senha_atual = st.text_input("Senha Atual", type="password")
                        nova_senha = st.text_input("Nova Senha", type="password")
                        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
                        
                        if st.form_submit_button("Alterar Senha", type="primary"):
                            from auth import verify_password, hash_password
                            
                            if not verify_password(senha_atual, usuario.password_hash):
                                st.error("Senha atual incorreta")
                            elif nova_senha != confirmar_senha:
                                st.error("As novas senhas não coincidem")
                            elif len(nova_senha) < 6:
                                st.error("A nova senha deve ter pelo menos 6 caracteres")
                            else:
                                usuario.password_hash = hash_password(nova_senha)
                                session.commit()
                                st.success("✅ Senha alterada com sucesso!")
            
            finally:
                session.close()
            
            st.divider()
            
            if st.button("🚪 Sair do Sistema", type="primary", use_container_width=True):
                for key in ['logged_in', 'username', 'user_id', 'is_admin']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Você saiu do sistema!")
                st.rerun()

# Rodapé
st.sidebar.markdown("---")
st.sidebar.caption("Sistema Financeiro Pessoal v1.0")

# Adicionar informações de versão e status
st.sidebar.markdown("---")
if st.session_state.get('is_admin', False):
    st.sidebar.success("👑 Modo Administrador")

# Botão de logout no sidebar
if st.sidebar.button("🚪 Sair", type="secondary", use_container_width=True):
    for key in ['logged_in', 'username', 'user_id', 'is_admin']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
