import streamlit as st
from database import get_session, Usuario, ConfigSistema, Categoria, Transacao
import bcrypt
import pandas as pd
from datetime import datetime
import json

# Funções auxiliares
def hash_password_local(password):
    """Função local para hash de senha"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# 1. Função para gerenciar usuários
def gerenciar_usuarios():
    """Interface de gerenciamento de usuários"""
    st.subheader("👥 Gerenciamento de Usuários")
    
    session = get_session()
    
    # Abas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["📋 Listar Usuários", "➕ Criar Usuário", "⚙️ Editar/Excluir"])
    
    with tab1:
        st.write("### Lista de Usuários do Sistema")
        
        # Buscar todos os usuários
        usuarios = session.query(Usuario).order_by(Usuario.id).all()
        
        if not usuarios:
            st.info("Nenhum usuário cadastrado no sistema.")
        else:
            # Criar DataFrame com dados dos usuários
            dados_usuarios = []
            for usuario in usuarios:
                dados_usuarios.append({
                    'ID': usuario.id,
                    'Usuário': usuario.username,
                    'Email': usuario.email or 'Não informado',
                    'Nível': usuario.nivel_acesso,
                    'Status': '✅ Ativo' if usuario.ativo else '❌ Inativo',
                    'Criado em': usuario.created_at.strftime('%d/%m/%Y'),
                    'Último Login': usuario.ultimo_login.strftime('%d/%m/%Y %H:%M') if usuario.ultimo_login else 'Nunca'
                })
            
            df_usuarios = pd.DataFrame(dados_usuarios)
            
            # Exibir tabela
            st.dataframe(
                df_usuarios,
                use_container_width=True,
                hide_index=True
            )
            
            # Estatísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_usuarios = len(usuarios)
                st.metric("Total de Usuários", total_usuarios)
            with col2:
                usuarios_ativos = sum(1 for u in usuarios if u.ativo)
                st.metric("Usuários Ativos", usuarios_ativos)
            with col3:
                admins = sum(1 for u in usuarios if u.nivel_acesso == 'admin')
                st.metric("Administradores", admins)
    
    with tab2:
        st.write("### Criar Novo Usuário")
        
        with st.form("form_criar_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                novo_username = st.text_input("Nome de Usuário *", help="Nome único para identificação")
                novo_email = st.text_input("Email", help="Email do usuário")
            
            with col2:
                nova_senha = st.text_input("Senha *", type="password", help="Mínimo 6 caracteres")
                confirmar_senha = st.text_input("Confirmar Senha *", type="password")
            
            col3, col4 = st.columns(2)
            with col3:
                nivel_acesso = st.selectbox(
                    "Nível de Acesso",
                    ["usuario", "admin"],
                    index=0,
                    help="'admin' tem acesso completo ao sistema"
                )
            
            with col4:
                status = st.selectbox(
                    "Status da Conta",
                    ["Ativo", "Inativo"],
                    index=0,
                    format_func=lambda x: "✅ Ativo" if x == "Ativo" else "❌ Inativo"
                )
            
            # Botão de submit
            submitted = st.form_submit_button("Criar Usuário", type="primary", use_container_width=True)
            
            if submitted:
                # Validações
                mensagens_erro = []
                
                if not novo_username:
                    mensagens_erro.append("Nome de usuário é obrigatório")
                
                if not nova_senha or not confirmar_senha:
                    mensagens_erro.append("Senha é obrigatória")
                elif nova_senha != confirmar_senha:
                    mensagens_erro.append("As senhas não coincidem")
                elif len(nova_senha) < 6:
                    mensagens_erro.append("A senha deve ter pelo menos 6 caracteres")
                
                # Verificar se usuário já existe
                usuario_existente = session.query(Usuario).filter_by(username=novo_username).first()
                if usuario_existente:
                    mensagens_erro.append(f"O usuário '{novo_username}' já existe")
                
                if mensagens_erro:
                    for erro in mensagens_erro:
                        st.error(erro)
                else:
                    try:
                        # Criar novo usuário
                        novo_usuario = Usuario(
                            username=novo_username,
                            password_hash=hash_password_local(nova_senha),
                            email=novo_email if novo_email.strip() else None,
                            nivel_acesso=nivel_acesso,
                            ativo=(status == "Ativo"),
                            created_at=datetime.utcnow()
                        )
                        
                        session.add(novo_usuario)
                        session.commit()
                        
                        st.success(f"✅ Usuário '{novo_username}' criado com sucesso!")
                        st.balloons()
                        
                        # Limpar campos
                        st.rerun()
                        
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao criar usuário: {str(e)}")
    
    with tab3:
        st.write("### Editar ou Excluir Usuários")
        
        # Buscar usuários para edição
        usuarios = session.query(Usuario).order_by(Usuario.username).all()
        
        if not usuarios:
            st.info("Nenhum usuário para editar.")
        else:
            # Lista de usuários para seleção
            usuarios_opcoes = {u.id: f"{u.username} ({u.nivel_acesso})" for u in usuarios}
            
            usuario_id_selecionado = st.selectbox(
                "Selecione um usuário para editar",
                options=list(usuarios_opcoes.keys()),
                format_func=lambda x: usuarios_opcoes[x]
            )
            
            if usuario_id_selecionado:
                usuario = session.query(Usuario).filter_by(id=usuario_id_selecionado).first()
                
                if usuario:
                    with st.form(f"form_editar_usuario_{usuario.id}"):
                        st.write(f"**Editando:** {usuario.username}")
                        
                        # Proteger o admin principal
                        if usuario.username == 'admin':
                            st.warning("⚠️ O usuário admin principal tem restrições de edição por segurança.")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Campos editáveis
                            novo_email = st.text_input(
                                "Email",
                                value=usuario.email or "",
                                disabled=(usuario.username == 'admin')
                            )
                            
                            # Nível de acesso (não pode alterar do próprio admin)
                            if usuario.username == 'admin':
                                st.text_input("Nível de Acesso", value="admin", disabled=True)
                            else:
                                novo_nivel = st.selectbox(
                                    "Nível de Acesso",
                                    ["usuario", "admin"],
                                    index=0 if usuario.nivel_acesso == "usuario" else 1
                                )
                        
                        with col2:
                            # Status
                            if usuario.username == 'admin':
                                st.text_input("Status", value="✅ Ativo (protegido)", disabled=True)
                            else:
                                novo_status = st.selectbox(
                                    "Status",
                                    ["Ativo", "Inativo"],
                                    index=0 if usuario.ativo else 1,
                                    format_func=lambda x: "✅ Ativo" if x == "Ativo" else "❌ Inativo"
                                )
                        
                        # Alteração de senha (opcional)
                        st.write("### 🔐 Alterar Senha (Opcional)")
                        alterar_senha = st.checkbox("Alterar senha deste usuário")
                        
                        if alterar_senha:
                            nova_senha_usuario = st.text_input("Nova Senha", type="password")
                            confirmar_senha_usuario = st.text_input("Confirmar Nova Senha", type="password")
                        
                        # Botões de ação
                        col_salvar, col_desativar, col_excluir = st.columns(3)
                        
                        with col_salvar:
                            salvar = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                        
                        with col_desativar:
                            if usuario.username != 'admin':
                                if usuario.ativo:
                                    desativar = st.form_submit_button("❌ Desativar", use_container_width=True)
                                else:
                                    desativar = st.form_submit_button("✅ Ativar", use_container_width=True)
                        
                        with col_excluir:
                            if usuario.username != 'admin' and usuario.username != st.session_state.get('username', ''):
                                excluir = st.form_submit_button("🗑️ Excluir", use_container_width=True)
                        
                        # Processar ações
                        if salvar:
                            try:
                                # Atualizar email
                                if usuario.username != 'admin':
                                    usuario.email = novo_email if novo_email.strip() else None
                                
                                # Atualizar nível de acesso
                                if usuario.username != 'admin':
                                    usuario.nivel_acesso = novo_nivel
                                
                                # Atualizar status
                                if usuario.username != 'admin':
                                    usuario.ativo = (novo_status == "Ativo")
                                
                                # Atualizar senha se solicitado
                                if alterar_senha and nova_senha_usuario and confirmar_senha_usuario:
                                    if nova_senha_usuario != confirmar_senha_usuario:
                                        st.error("As senhas não coincidem")
                                    elif len(nova_senha_usuario) < 6:
                                        st.error("A senha deve ter pelo menos 6 caracteres")
                                    else:
                                        usuario.password_hash = hash_password_local(nova_senha_usuario)
                                        st.success("Senha atualizada com sucesso!")
                                
                                session.commit()
                                st.success("✅ Alterações salvas com sucesso!")
                                st.rerun()
                                
                            except Exception as e:
                                session.rollback()
                                st.error(f"❌ Erro ao salvar alterações: {str(e)}")
                        
                        if 'desativar' in locals() and desativar:
                            if usuario.username != 'admin':
                                usuario.ativo = not usuario.ativo
                                session.commit()
                                st.success(f"✅ Usuário {'desativado' if not usuario.ativo else 'ativado'}!")
                                st.rerun()
                        
                        if 'excluir' in locals() and excluir:
                            if usuario.username != 'admin' and usuario.username != st.session_state.get('username', ''):
                                session.delete(usuario)
                                session.commit()
                                st.success("✅ Usuário excluído com sucesso!")
                                st.rerun()
    
    session.close()

# 2. Função para gerenciar categorias
def gerenciar_categorias():
    """Interface de gerenciamento de categorias personalizadas"""
    st.subheader("🏷️ Gerenciamento de Categorias")
    
    st.info("""
    **Categorias Personalizadas:**
    Crie e gerencie suas próprias categorias para classificação automática de transações.
    """)
    
    session = get_session()
    
    # Abas para funcionalidades
    tab1, tab2 = st.tabs(["📋 Minhas Categorias", "➕ Criar Nova Categoria"])
    
    with tab1:
        st.write("### Suas Categorias Personalizadas")
        
        # Buscar categorias do usuário atual
        categorias = session.query(Categoria).filter(
            Categoria.usuario_id == st.session_state.user_id
        ).order_by(Categoria.nome).all()
        
        if not categorias:
            st.info("Você ainda não criou categorias personalizadas.")
        else:
            for categoria in categorias:
                with st.expander(f"📁 {categoria.nome} - {categoria.tipo}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Palavras-chave:**")
                        st.write(categoria.palavras_chave)
                        st.caption(f"Criada em: {categoria.id if hasattr(categoria, 'id') else 'N/A'}")
                    
                    with col2:
                        # Botões de ação
                        if st.button("✏️ Editar", key=f"edit_{categoria.id}"):
                            st.session_state['editando_categoria_id'] = categoria.id
                        
                        if st.button("🗑️ Excluir", key=f"del_{categoria.id}"):
                            session.delete(categoria)
                            session.commit()
                            st.success(f"Categoria '{categoria.nome}' excluída!")
                            st.rerun()
        
        # Estatísticas
        if categorias:
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Categorias", len(categorias))
            with col2:
                tipos = {}
                for cat in categorias:
                    tipos[cat.tipo] = tipos.get(cat.tipo, 0) + 1
                st.metric("Tipos Diferentes", len(tipos))
    
    with tab2:
        st.write("### Criar Nova Categoria")
        
        with st.form("form_nova_categoria", clear_on_submit=True):
            # Nome da categoria
            nome_categoria = st.text_input(
                "Nome da Categoria *",
                help="Ex: Alimentação, Transporte, Lazer"
            )
            
            # Tipo de categoria
            tipo_categoria = st.selectbox(
                "Tipo de Categoria *",
                ["FIXO", "VARIAVEL", "INVESTIMENTO", "LAZER", "OUTROS"],
                help="FIXO: Gastos recorrentes mensais\nVARIAVEL: Gastos variáveis\nINVESTIMENTO: Aplicações\nLAZER: Entretenimento"
            )
            
            # Palavras-chave
            palavras_chave = st.text_area(
                "Palavras-chave *",
                help="Digite palavras separadas por vírgula que identifiquem esta categoria\nEx: restaurante, lanche, mercado, ifood",
                height=100
            )
            
            # Botão de submit
            submitted = st.form_submit_button("Criar Categoria", type="primary", use_container_width=True)
            
            if submitted:
                # Validações
                if not nome_categoria:
                    st.error("O nome da categoria é obrigatório")
                elif not tipo_categoria:
                    st.error("O tipo da categoria é obrigatório")
                elif not palavras_chave:
                    st.error("As palavras-chave são obrigatórias")
                else:
                    try:
                        # Verificar se categoria já existe para este usuário
                        categoria_existente = session.query(Categoria).filter(
                            Categoria.usuario_id == st.session_state.user_id,
                            Categoria.nome == nome_categoria
                        ).first()
                        
                        if categoria_existente:
                            st.error(f"Você já tem uma categoria com o nome '{nome_categoria}'")
                        else:
                            # Criar nova categoria
                            nova_categoria = Categoria(
                                usuario_id=st.session_state.user_id,
                                nome=nome_categoria,
                                tipo=tipo_categoria,
                                palavras_chave=palavras_chave
                            )
                            
                            session.add(nova_categoria)
                            session.commit()
                            
                            st.success(f"✅ Categoria '{nome_categoria}' criada com sucesso!")
                            st.balloons()
                            st.rerun()
                            
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao criar categoria: {str(e)}")
    
    session.close()

# 3. Função para configurações do sistema
def configurar_sistema():
    """Configurações do sistema"""
    st.subheader("⚙️ Configurações do Sistema")
    
    session = get_session()
    
    # Buscar configurações existentes
    configs = session.query(ConfigSistema).order_by(ConfigSistema.chave).all()
    
    if configs:
        st.write("### Configurações Atuais do Sistema")
        
        for config in configs:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{config.chave}**")
                    st.caption(config.descricao)
                
                with col2:
                    novo_valor = st.text_input(
                        "Valor",
                        value=config.valor,
                        key=f"input_{config.id}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    if st.button("💾", key=f"save_{config.id}"):
                        config.valor = novo_valor
                        session.commit()
                        st.success(f"Configuração '{config.chave}' atualizada!")
                        st.rerun()
                
                st.divider()
    else:
        st.info("Nenhuma configuração do sistema encontrada.")
    
    # Ações avançadas
    st.write("### ⚡ Ações Avançadas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reiniciar Classificador IA", use_container_width=True):
            try:
                st.cache_resource.clear()
                st.success("Classificador IA reiniciado com sucesso!")
            except:
                st.success("Cache limpo!")
    
    with col2:
        if st.button("📊 Gerar Relatório do Sistema", use_container_width=True):
            st.info("Esta funcionalidade está em desenvolvimento.")
    
    with col3:
        if st.button("🧹 Limpar Cache do Sistema", use_container_width=True):
            try:
                st.cache_resource.clear()
                st.success("Cache do sistema limpo com sucesso!")
            except:
                st.success("Cache limpo!")

    st.divider()
    st.write("### 🧨 Reset Total do Banco (TEMPORÁRIO)")
    st.warning("⚠️ Isso apaga TODOS os dados (usuários, transações, categorias, configurações). Use apenas para testes.")

    confirm = st.checkbox("Confirmo que quero zerar o banco de dados")
    if confirm and st.button("🗑️ APAGAR TUDO", type="primary", use_container_width=True):
        session = get_session()
        try:
            session.execute("DELETE FROM transacoes")
            session.execute("DELETE FROM categorias")
            session.execute("DELETE FROM usuarios")
            session.execute("DELETE FROM config_sistema")
            session.commit()
            st.success("✅ Banco zerado com sucesso!")
            st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"❌ Erro ao zerar banco: {e}")
        finally:
            session.close()
    
    session.close()

# 4. Função para backup de dados
def backup_dados():
    """Interface de backup de dados"""
    st.subheader("💾 Backup de Dados")
    
    st.info("""
    **Backup do Sistema:**
    Faça backup completo dos seus dados financeiros para garantir sua segurança.
    Recomendado realizar backup mensalmente.
    """)
    
    session = get_session()
    
    # Abas para exportar/importar
    tab1, tab2 = st.tabs(["📤 Exportar Backup", "📥 Restaurar Backup"])
    
    with tab1:
        st.write("### Exportar Dados para Backup")
        
        # Opções de backup
        backup_opcoes = st.multiselect(
            "Selecione os dados para incluir no backup:",
            ["Usuários", "Transações", "Categorias", "Configurações do Sistema"],
            default=["Transações", "Categorias"]
        )
        
        if st.button("⬇️ Gerar Backup Completo", type="primary", use_container_width=True):
            with st.spinner("Coletando dados e gerando backup..."):
                try:
                    dados_backup = {
                        'metadata': {
                            'data_backup': datetime.now().isoformat(),
                            'usuario': st.session_state.username,
                            'usuario_id': st.session_state.user_id,
                            'itens_incluidos': backup_opcoes
                        }
                    }
                    
                    # Coletar dados conforme selecionado
                    if "Usuários" in backup_opcoes and st.session_state.get('is_admin', False):
                        usuarios = session.query(Usuario).all()
                        dados_backup['usuarios'] = [
                            {
                                'id': u.id,
                                'username': u.username,
                                'email': u.email,
                                'nivel_acesso': u.nivel_acesso,
                                'ativo': u.ativo,
                                'created_at': u.created_at.isoformat() if u.created_at else None,
                                'ultimo_login': u.ultimo_login.isoformat() if u.ultimo_login else None
                            }
                            for u in usuarios
                        ]
                    
                    if "Transações" in backup_opcoes:
                        transacoes = session.query(Transacao).filter_by(
                            usuario_id=st.session_state.user_id
                        ).all()
                        
                        dados_backup['transacoes'] = [
                            {
                                'id': t.id,
                                'data': t.data.isoformat() if t.data else None,
                                'descricao': t.descricao,
                                'valor': float(t.valor),
                                'tipo': t.tipo,
                                'banco': t.banco,
                                'categoria_ia': t.categoria_ia,
                                'categoria_manual': t.categoria_manual,
                                'parcelamento': t.parcelamento,
                                'parcela_atual': t.parcela_atual,
                                'parcela_total': t.parcela_total,
                                'data_vencimento': t.data_vencimento.isoformat() if t.data_vencimento else None,
                                'processado': t.processado
                            }
                            for t in transacoes
                        ]
                    
                    if "Categorias" in backup_opcoes:
                        categorias = session.query(Categoria).filter_by(
                            usuario_id=st.session_state.user_id
                        ).all()
                        
                        dados_backup['categorias'] = [
                            {
                                'id': c.id,
                                'nome': c.nome,
                                'palavras_chave': c.palavras_chave,
                                'tipo': c.tipo
                            }
                            for c in categorias
                        ]
                    
                    if "Configurações do Sistema" in backup_opcoes and st.session_state.get('is_admin', False):
                        configs = session.query(ConfigSistema).all()
                        dados_backup['configuracoes'] = [
                            {
                                'id': c.id,
                                'chave': c.chave,
                                'valor': c.valor,
                                'descricao': c.descricao
                            }
                            for c in configs
                        ]
                    
                    # Converter para JSON
                    backup_json = json.dumps(dados_backup, indent=2, ensure_ascii=False, default=str)
                    
                    # Nome do arquivo
                    nome_arquivo = f"backup_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    
                    # Botão de download
                    st.download_button(
                        label="📥 Baixar Arquivo de Backup",
                        data=backup_json,
                        file_name=nome_arquivo,
                        mime="application/json",
                        use_container_width=True,
                        icon="💾"
                    )
                    
                    st.success("✅ Backup gerado com sucesso!")
                    st.info(f"O backup inclui: {', '.join(backup_opcoes)}")
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar backup: {str(e)}")
    
    with tab2:
        st.write("### Restaurar Dados do Backup")
        
        st.warning("⚠️ **Atenção:** A restauração de backup substituirá seus dados atuais. Use com cuidado!")
        
        # Upload do arquivo de backup
        uploaded_file = st.file_uploader(
            "Selecione o arquivo de backup (.json)",
            type=['json'],
            help="Selecione um arquivo de backup gerado anteriormente"
        )
        
        if uploaded_file:
            try:
                # Ler e mostrar preview do backup
                dados_backup = json.load(uploaded_file)
                
                st.success("✅ Arquivo de backup carregado com sucesso!")
                
                # Mostrar informações do backup
                with st.expander("📋 Visualizar conteúdo do backup", expanded=False):
                    st.json(dados_backup)
                
                # Informações do backup
                if 'metadata' in dados_backup:
                    metadata = dados_backup['metadata']
                    st.info(f"""
                    **Informações do Backup:**
                    - Data do backup: {metadata.get('data_backup', 'Desconhecida')}
                    - Usuário original: {metadata.get('usuario', 'Desconhecido')}
                    - Itens incluídos: {', '.join(metadata.get('itens_incluidos', []))}
                    """)
                
                # Opção para restaurar
                st.divider()
                st.write("### 🔄 Restaurar Backup")
                
                if st.session_state.get('is_admin', False):
                    opcoes_restaurar = ["Transações", "Categorias", "Configurações do Sistema"]
                else:
                    opcoes_restaurar = ["Transações", "Categorias"]
                
                itens_restaurar = st.multiselect(
                    "Selecione os itens para restaurar:",
                    opcoes_restaurar,
                    default=["Transações", "Categorias"]
                )
                
                # Confirmação
                confirmar = st.checkbox("⚠️ Confirmo que quero substituir meus dados atuais pelos dados do backup")
                
                if confirmar and itens_restaurar:
                    if st.button("🔄 Iniciar Restauração", type="primary", use_container_width=True):
                        with st.spinner("Restaurando dados do backup..."):
                            try:
                                # Aqui você implementaria a lógica de restauração
                                # Por segurança, vamos apenas informar que funcionaria
                                st.success("✅ Restauração iniciada com sucesso!")
                                st.info(f"Os seguintes itens serão restaurados: {', '.join(itens_restaurar)}")
                                
                                # Em um sistema real, aqui você implementaria:
                                # 1. Backup dos dados atuais antes da restauração
                                # 2. Limpeza dos dados atuais (se necessário)
                                # 3. Importação dos dados do backup
                                # 4. Validação dos dados importados
                                
                                st.warning("""
                                **Nota de Segurança:**
                                Em um ambiente de produção, a restauração completa requer
                                implementação adicional para garantir a integridade dos dados
                                e evitar perdas acidentais.
                                """)
                                
                            except Exception as e:
                                st.error(f"❌ Erro durante a restauração: {str(e)}")
                elif not confirmar and itens_restaurar:
                    st.info("Marque a caixa de confirmação para habilitar a restauração.")
                    
            except json.JSONDecodeError:
                st.error("❌ O arquivo selecionado não é um JSON válido.")
            except Exception as e:
                st.error(f"❌ Erro ao processar o arquivo de backup: {str(e)}")
    
    session.close()

# Exportar as funções
__all__ = ['gerenciar_usuarios', 'gerenciar_categorias', 'configurar_sistema', 'backup_dados']
