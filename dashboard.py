import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
from database import get_session, Transacao

def carregar_dados(usuario_id, periodo_meses=12):
    session = get_session()
    try:
        data_inicio = datetime.now() - timedelta(days=periodo_meses*30)
        
        transacoes = session.query(Transacao).filter(
            Transacao.usuario_id == usuario_id,
            Transacao.data >= data_inicio
        ).all()
        
        dados = []
        for t in transacoes:
            dados.append({
                'Data': t.data,
                'Descrição': t.descricao,
                'Valor': t.valor,
                'Tipo': t.tipo,
                'Banco': t.banco,
                'Categoria': t.categoria_manual if t.categoria_manual else t.categoria_ia,
                'Parcelamento': 'Sim' if t.parcelamento else 'Não',
                'Parcela': f"{t.parcela_atual}/{t.parcela_total}" if t.parcelamento else None
            })
        
        return pd.DataFrame(dados)
    finally:
        session.close()

def criar_dashboard(df, usuario_id):
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bancos = ['Todos'] + list(df['Banco'].unique())
        banco_selecionado = st.selectbox('Banco', bancos)
    
    with col2:
        categorias = ['Todas'] + list(df['Categoria'].dropna().unique())
        categoria_selecionada = st.selectbox('Categoria', categorias)
    
    with col3:
        tipo_selecionado = st.selectbox('Tipo', ['Todos', 'DEBITO', 'CREDITO'])
    
    # Aplicar filtros
    if banco_selecionado != 'Todos':
        df = df[df['Banco'] == banco_selecionado]
    if categoria_selecionada != 'Todas':
        df = df[df['Categoria'] == categoria_selecionada]
    if tipo_selecionado != 'Todos':
        df = df[df['Tipo'] == tipo_selecionado]
    
    # Métricas principais
    st.subheader("📊 Métricas Financeiras")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_gastos = df[df['Valor'] < 0]['Valor'].sum() * -1
        st.metric("Total Gastos", f"R$ {total_gastos:,.2f}")
    
    with col2:
        total_ganhos = df[df['Valor'] > 0]['Valor'].sum()
        st.metric("Total Ganhos", f"R$ {total_ganhos:,.2f}")
    
    with col3:
        saldo = total_ganhos - total_gastos
        st.metric("Saldo", f"R$ {saldo:,.2f}")
    
    with col4:
        media_mensal = df[df['Valor'] < 0].groupby(
            df['Data'].dt.to_period('M')
        )['Valor'].sum().mean() * -1
        st.metric("Média Mensal", f"R$ {media_mensal:,.2f}")
    
    # Gráfico 1: Gastos por Categoria
    st.subheader("📈 Gastos por Categoria")
    
    gastos_por_categoria = df[df['Valor'] < 0].groupby('Categoria')['Valor'].sum().abs()
    
    fig1 = go.Figure(data=[
        go.Pie(
            labels=gastos_por_categoria.index,
            values=gastos_por_categoria.values,
            hole=.3
        )
    ])
    fig1.update_layout(title='Distribuição de Gastos por Categoria')
    st.plotly_chart(fig1, use_container_width=True)
    
    # Gráfico 2: Evolução Mensal (12 meses lado a lado)
    st.subheader("📅 Evolução Mensal dos Gastos")
    
    df_mensal = df.copy()
    df_mensal['Mês'] = df_mensal['Data'].dt.to_period('M').astype(str)
    df_mensal['Valor_Absoluto'] = df_mensal['Valor'].abs()
    
    # Criar subplots com 12 meses
    meses = sorted(df_mensal['Mês'].unique())[-12:]  # Últimos 12 meses
    
    fig2 = make_subplots(
        rows=3, cols=4,
        subplot_titles=meses,
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    for idx, mes in enumerate(meses):
        row = idx // 4 + 1
        col = idx % 4 + 1
        
        dados_mes = df_mensal[df_mensal['Mês'] == mes]
        gastos_categoria = dados_mes[dados_mes['Valor'] < 0].groupby('Categoria')['Valor_Absoluto'].sum()
        
        fig2.add_trace(
            go.Bar(
                x=gastos_categoria.values,
                y=gastos_categoria.index,
                orientation='h',
                name=mes
            ),
            row=row, col=col
        )
        
        fig2.update_xaxes(title_text="Valor (R$)", row=row, col=col)
    
    fig2.update_layout(height=900, showlegend=False, title_text="Gastos por Categoria - Últimos 12 Meses")
    st.plotly_chart(fig2, use_container_width=True)
    
    # Gráfico 3: Comparativo entre Bancos
    st.subheader("🏦 Comparativo entre Bancos")
    
    gastos_por_banco = df[df['Valor'] < 0].groupby('Banco')['Valor'].sum().abs()
    
    fig3 = px.bar(
        x=gastos_por_banco.index,
        y=gastos_por_banco.values,
        title="Gastos por Banco",
        labels={'x': 'Banco', 'y': 'Valor (R$)'}
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    # Tabela de Previsão de Gastos Futuros
    st.subheader("🔮 Previsão de Gastos Futuros")
    
    # Identificar parcelamentos
    df_parcelas = df[df['Parcelamento'] == 'Sim'].copy()
    
    if not df_parcelas.empty:
        st.write("Parcelamentos em andamento:")
        st.dataframe(
            df_parcelas[['Descrição', 'Valor', 'Parcela', 'Banco', 'Categoria']],
            use_container_width=True
        )
    
    # Previsão com base em média móvel
    df_previsao = df[df['Valor'] < 0].copy()
    df_previsao['Mês'] = df_previsao['Data'].dt.to_period('M')
    
    media_gastos = df_previsao.groupby('Mês')['Valor'].sum().abs().tail(6).mean()
    
    col1, col2, col3 = st.columns(3)
    proximos_meses = ['Próximo Mês', '2 Meses', '3 Meses']
    
    for i, mes in enumerate(proximos_meses):
        with [col1, col2, col3][i]:
            st.metric(f"Previsão {mes}", f"R$ {media_gastos:,.2f}")
    
    return df