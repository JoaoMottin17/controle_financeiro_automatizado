import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
from database import get_session, Transacao
import calendar

@st.cache_data(ttl=300)
def carregar_dados(usuario_id, periodo_meses=12):
    """Carrega transações do banco de dados"""
    session = get_session()
    try:
        data_inicio = datetime.now() - timedelta(days=periodo_meses*30)
        
        transacoes = session.query(Transacao).filter(
            Transacao.usuario_id == usuario_id,
            Transacao.data >= data_inicio
        ).order_by(Transacao.data.desc()).all()
        
        dados = []
        for t in transacoes:
            # Usar apenas categoria da IA
            categoria = t.categoria_ia
            
            dados.append({
                'ID': t.id,
                'Data': t.data,
                'Descrição': t.descricao,
                'Valor': t.valor,
                'Tipo': t.tipo,
                'Banco': t.banco,
                'Centro_Custo': t.centro_custo,
                'Categoria': categoria or 'NÃO CLASSIFICADA',
                'Categoria_IA': t.categoria_ia,
                'Confianca_IA': t.confianca_ia,
                'Categoria_Manual': t.categoria_manual,
                'Parcelamento': 'Sim' if t.parcelamento else 'Não',
                'Parcela': f"{t.parcela_atual}/{t.parcela_total}" if t.parcelamento else None,
                'Data_Vencimento': t.data_vencimento,
                'Processado': t.processado
            })
        
        df = pd.DataFrame(dados)
        
        if not df.empty:
            # Converter datas
            df['Data'] = pd.to_datetime(df['Data'])
            if 'Data_Vencimento' in df.columns:
                df['Data_Vencimento'] = pd.to_datetime(df['Data_Vencimento'], errors='coerce')
            
            # Criar colunas auxiliares
            df['Ano'] = df['Data'].dt.year
            df['Mes'] = df['Data'].dt.month
            df['Mes_Nome'] = df['Data'].dt.strftime('%b/%Y')
            df['Dia'] = df['Data'].dt.day
            df['Semana'] = df['Data'].dt.isocalendar().week
            df['Valor_Absoluto'] = df['Valor'].abs()
            df['Valor_Positivo'] = df['Valor'].apply(lambda x: x if x > 0 else 0)
            df['Valor_Negativo'] = df['Valor'].apply(lambda x: abs(x) if x < 0 else 0)
        
        return df
        
    finally:
        session.close()

def criar_dashboard(df, usuario_id):
    """Cria o dashboard com visualizações"""
    
    # Verificar se há dados
    if df.empty:
        st.warning("Nenhuma transação encontrada para o período selecionado.")
        return pd.DataFrame()
    
    # Filtros
    st.sidebar.header("🔍 Filtros")
    
    # Filtro de data
    min_date = df['Data'].min().date()
    max_date = df['Data'].max().date()
    
    date_range = st.sidebar.date_input(
        "Período",
        value=(max_date - timedelta(days=90), max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        df = df[(df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)]
    
    # Filtro de banco
    bancos = ['Todos'] + sorted(df['Banco'].unique().tolist())
    banco_selecionado = st.sidebar.selectbox('Banco', bancos)
    
    if banco_selecionado != 'Todos':
        df = df[df['Banco'] == banco_selecionado]
    
    # Filtro de categoria
    categorias = ['Todas'] + sorted(df['Categoria'].unique().tolist())
    categoria_selecionada = st.sidebar.selectbox('Categoria', categorias)
    
    if categoria_selecionada != 'Todas':
        df = df[df['Categoria'] == categoria_selecionada]

    # Filtro de centro de custo
    centros = ['Todos'] + sorted(df['Centro_Custo'].fillna('Não informado').unique().tolist())
    centro_selecionado = st.sidebar.selectbox('Centro de Custo', centros)
    if centro_selecionado != 'Todos':
        df = df[df['Centro_Custo'].fillna('Não informado') == centro_selecionado]
    
    # Filtro de tipo
    tipo_selecionado = st.sidebar.selectbox('Tipo', ['Todos', 'DEBITO', 'CREDITO'])
    
    if tipo_selecionado != 'Todos':
        df = df[df['Tipo'] == tipo_selecionado]
    
    # Filtro de valor mínimo
    valor_min = st.sidebar.number_input(
        "Valor Mínimo (R$)", 
        min_value=0.0, 
        value=0.0,
        step=10.0
    )
    
    if valor_min > 0:
        df = df[df['Valor_Absoluto'] >= valor_min]
    
    # Métricas principais (saúde financeira)
    st.subheader("📊 Saúde Financeira (Resumo)")
    
    total_gastos = df[df['Tipo'] == 'DEBITO']['Valor_Absoluto'].sum()
    total_ganhos = df[df['Tipo'] == 'CREDITO']['Valor'].sum()
    saldo = total_ganhos - total_gastos
    taxa_gasto = (total_gastos / total_ganhos) if total_ganhos > 0 else 0.0
    taxa_poupanca = (saldo / total_ganhos) if total_ganhos > 0 else 0.0
    dias_periodo = (df['Data'].max().date() - df['Data'].min().date()).days + 1 if not df.empty else 0
    gasto_medio_dia = (total_gastos / dias_periodo) if dias_periodo > 0 else 0.0
    ticket_medio = df[df['Tipo'] == 'DEBITO']['Valor_Absoluto'].mean() if not df.empty else 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Gastos Totais", f"R$ {total_gastos:,.2f}")
        st.metric("Gasto Médio/Dia", f"R$ {gasto_medio_dia:,.2f}")
    with col2:
        st.metric("Ganhos Totais", f"R$ {total_ganhos:,.2f}")
        st.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
    with col3:
        st.metric("Saldo", f"R$ {saldo:,.2f}", delta=f"R$ {saldo:+,.2f}" if saldo != 0 else "R$ 0,00")
        st.metric("Taxa de Poupança", f"{taxa_poupanca*100:,.1f}%")

    st.caption("Taxa de Poupança = Saldo / Ganhos. Taxa de Gasto = Gastos / Ganhos.")
    
    st.markdown("---")

    # Insights rapidos
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("### 🔎 Principais Categorias de Gasto")
        top_cats = df[df['Tipo'] == 'DEBITO'].groupby('Categoria')['Valor_Absoluto'].sum().sort_values(ascending=False).head(5)
        if not top_cats.empty:
            st.dataframe(
                top_cats.reset_index().rename(columns={'Valor': 'Total'}), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem gastos para exibir.")
    with col_b:
        st.write("### 🏦 Bancos com Mais Gastos")
        top_bancos = df[df['Tipo'] == 'DEBITO'].groupby('Banco')['Valor_Absoluto'].sum().sort_values(ascending=False).head(5)
        if not top_bancos.empty:
            st.dataframe(
                top_bancos.reset_index().rename(columns={'Valor': 'Total'}), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem gastos para exibir.")
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Análise Geral", 
        "📅 Evolução Mensal", 
        "🏦 Por Banco", 
        "📋 Detalhes"
    ])
    
    with tab1:
        # Gráfico 1: Gastos por Categoria (Pizza)
        st.subheader("📊 Distribuição de Gastos por Categoria")
        
        gastos_por_categoria = df[df['Tipo'] == 'DEBITO'].groupby('Categoria')['Valor_Absoluto'].sum()
        
        if not gastos_por_categoria.empty:
            fig1 = go.Figure(data=[
                go.Pie(
                    labels=gastos_por_categoria.index,
                    values=gastos_por_categoria.values,
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='inside',
                    marker=dict(colors=px.colors.qualitative.Set3)
                )
            ])
            
            fig1.update_layout(
                title='',
                height=400,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                )
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados de gastos para exibir.")
        
        # Gráfico 2: Evolução de Gastos e Ganhos (Linha)
        st.subheader("📈 Evolução de Gastos e Ganhos")
        
        df_mensal = df.copy()
        df_mensal['Mes_Ano'] = df_mensal['Data'].dt.strftime('%Y-%m')
        
        evolucao = df_mensal.groupby(['Mes_Ano', 'Tipo'])['Valor_Absoluto'].sum().unstack(fill_value=0)
        
        if not evolucao.empty:
            fig2 = go.Figure()
            
            if 'DEBITO' in evolucao.columns:
                fig2.add_trace(go.Scatter(
                    x=evolucao.index,
                    y=evolucao['DEBITO'],
                    mode='lines+markers',
                    name='Gastos',
                    line=dict(color='red', width=3),
                    marker=dict(size=8)
                ))
            
            if 'CREDITO' in evolucao.columns:
                fig2.add_trace(go.Scatter(
                    x=evolucao.index,
                    y=evolucao['CREDITO'],
                    mode='lines+markers',
                    name='Ganhos',
                    line=dict(color='green', width=3),
                    marker=dict(size=8)
                ))
            
            fig2.update_layout(
                title='',
                xaxis_title='Mês',
                yaxis_title='Valor (R$)',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolução.")
    
    with tab2:
        # Gráfico 3: Comparativo Mensal (12 meses lado a lado)
        st.subheader("📅 Comparativo Mensal - Últimos 12 Meses")
        
        # Obter últimos 12 meses (baseado no início do mês)
        hoje = datetime.now()
        inicio_mes_atual = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        meses_dt = pd.date_range(end=inicio_mes_atual, periods=12, freq='MS')
        meses = [d.strftime('%b/%Y') for d in meses_dt]
        
        # Filtrar dados dos últimos 12 meses
        data_limite = meses_dt[0]
        df_12meses = df[df['Data'] >= data_limite].copy()
        
        if not df_12meses.empty:
            # Criar subplots
            fig3 = make_subplots(
                rows=3, cols=4,
                subplot_titles=meses,
                vertical_spacing=0.15,
                horizontal_spacing=0.1
            )
            
            for idx, mes in enumerate(meses):
                row = idx // 4 + 1
                col = idx % 4 + 1
                
                # Filtrar dados do mês
                mes_dt = meses_dt[idx]
                dados_mes = df_12meses[
                    (df_12meses['Data'].dt.month == mes_dt.month) & 
                    (df_12meses['Data'].dt.year == mes_dt.year)
                ]
                
                gastos_categoria = dados_mes[dados_mes['Tipo'] == 'DEBITO'].groupby('Categoria')['Valor_Absoluto'].sum()
                
                if not gastos_categoria.empty:
                    fig3.add_trace(
                        go.Bar(
                            x=gastos_categoria.values,
                            y=gastos_categoria.index,
                            orientation='h',
                            name=mes,
                            marker_color='lightcoral'
                        ),
                        row=row, col=col
                    )
                
                fig3.update_xaxes(title_text="Valor (R$)", row=row, col=col, range=[0, gastos_categoria.max() * 1.1 if not gastos_categoria.empty else 0])
            
            fig3.update_layout(
                height=900,
                showlegend=False,
                title_text="",
                title_x=0.5
            )
            
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Dados insuficientes para os últimos 12 meses.")
    
    with tab3:
        # Gráfico 4: Comparativo entre Bancos
        st.subheader("🏦 Análise por Banco")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gastos por banco
            st.write("#### Gastos por Banco")
            gastos_por_banco = df[df['Tipo'] == 'DEBITO'].groupby('Banco')['Valor_Absoluto'].sum()
            
            if not gastos_por_banco.empty:
                fig4a = px.bar(
                    x=gastos_por_banco.index,
                    y=gastos_por_banco.values,
                    title="",
                    labels={'x': 'Banco', 'y': 'Valor Gasto (R$)'},
                    color=gastos_por_banco.values,
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig4a, use_container_width=True)
            else:
                st.info("Sem gastos por banco.")
        
        with col2:
            # Ganhos por banco
            st.write("#### Ganhos por Banco")
            ganhos_por_banco = df[df['Tipo'] == 'CREDITO'].groupby('Banco')['Valor'].sum()
            
            if not ganhos_por_banco.empty:
                fig4b = px.bar(
                    x=ganhos_por_banco.index,
                    y=ganhos_por_banco.values,
                    title="",
                    labels={'x': 'Banco', 'y': 'Valor Ganho (R$)'},
                    color=ganhos_por_banco.values,
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig4b, use_container_width=True)
            else:
                st.info("Sem ganhos por banco.")
    
    with tab4:
        # Previsão de Gastos Futuros
        st.subheader("🔮 Previsão de Gastos Futuros")
        
        # Identificar parcelamentos
        df_parcelas = df[df['Parcelamento'] == 'Sim'].copy()
        
        if not df_parcelas.empty:
            st.write("#### Parcelamentos em Andamento")
            
            parcelas_ativas = []
            for _, row in df_parcelas.iterrows():
                if row['Parcela']:
                    atual, total = map(int, row['Parcela'].split('/'))
                    if atual < total:
                        parcelas_ativas.append({
                            'Descrição': row['Descrição'],
                            'Valor Parcela': abs(row['Valor']),
                            'Parcela': row['Parcela'],
                            'Próximas Parcelas': total - atual,
                            'Total Restante': abs(row['Valor']) * (total - atual),
                            'Banco': row['Banco'],
                            'Categoria': row['Categoria']
                        })
            
            if parcelas_ativas:
                df_previsao = pd.DataFrame(parcelas_ativas)
                st.dataframe(
                    df_previsao,
                    use_container_width=True,
                    column_config={
                        "Valor Parcela": st.column_config.NumberColumn(
                            "Valor Parcela (R$)",
                            format="R$ %.2f"
                        ),
                        "Total Restante": st.column_config.NumberColumn(
                            "Total Restante (R$)",
                            format="R$ %.2f"
                        )
                    }
                )
                
                # Calcular totais
                col1, col2 = st.columns(2)
                with col1:
                    total_mensal = df_previsao['Valor Parcela'].sum()
                    st.metric("Total Mensal Parcelas", f"R$ {total_mensal:,.2f}")
                
                with col2:
                    total_restante = df_previsao['Total Restante'].sum()
                    st.metric("Total Restante", f"R$ {total_restante:,.2f}")
            else:
                st.info("Nenhum parcelamento ativo encontrado.")
        else:
            st.info("Nenhum parcelamento encontrado.")
        
        st.markdown("---")
        
        # Previsão com base em média móvel
        st.write("#### Previsão Baseada em Histórico")
        
        df_previsao_historico = df[df['Tipo'] == 'DEBITO'].copy()
        
        if len(df_previsao_historico) >= 3:
            df_previsao_historico['Mes'] = df_previsao_historico['Data'].dt.to_period('M')
            
            media_gastos = df_previsao_historico.groupby('Mes')['Valor_Absoluto'].sum().tail(6).mean()
            
            col1, col2, col3 = st.columns(3)
            
            for i, mes in enumerate(['Próximo Mês', '2 Meses', '3 Meses']):
                with [col1, col2, col3][i]:
                    st.metric(
                        f"Previsão {mes}", 
                        f"R$ {media_gastos:,.2f}",
                        delta=None
                    )
        else:
            st.info("Dados insuficientes para previsão histórica.")
    
    return df
