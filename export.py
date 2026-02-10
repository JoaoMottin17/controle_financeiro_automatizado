import pandas as pd
from datetime import datetime
from database import get_session, Transacao, Usuario, Categoria
import io
import json

def exportar_para_excel(usuario_id):
    """Exporta dados do usuário para Excel"""
    session = get_session()
    
    try:
        # Buscar transações do usuário
        transacoes = session.query(Transacao).filter_by(usuario_id=usuario_id).all()
        
        if not transacoes:
            return None
        
        # Preparar dados
        dados = []
        for t in transacoes:
            dados.append({
                'Data': t.data.strftime('%Y-%m-%d') if t.data else '',
                'Descrição': t.descricao or '',
                'Valor': float(t.valor),
                'Tipo': t.tipo or '',
                'Banco': t.banco or '',
                'Centro de Custo': t.centro_custo or '',
                'Categoria IA': t.categoria_ia or '',
                'Categoria Manual': t.categoria_manual or '',
                'Parcelamento': 'Sim' if t.parcelamento else 'Não',
                'Parcela': f"{t.parcela_atual}/{t.parcela_total}" if t.parcelamento and t.parcela_atual and t.parcela_total else '',
                'Tags': t.tags or ''
            })
        
        df = pd.DataFrame(dados)
        
        # Criar arquivo Excel
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Planilha 1: Transações
            df.to_excel(writer, sheet_name='Transações', index=False)
            
            # Planilha 2: Resumo por categoria
            if not df.empty:
                resumo_df = df.copy()
                resumo_df['Categoria'] = resumo_df['Categoria Manual'].fillna(resumo_df['Categoria IA'])
                
                resumo_categoria = resumo_df.groupby('Categoria').agg({
                    'Valor': ['sum', 'count'],
                    'Descrição': 'first'
                }).round(2)
                
                resumo_categoria.columns = ['Total', 'Quantidade', 'Exemplo']
                resumo_categoria = resumo_categoria.reset_index()
                resumo_categoria.to_excel(writer, sheet_name='Resumo Categorias', index=False)
            
            # Planilha 3: Resumo mensal
            if not df.empty and 'Data' in df.columns:
                try:
                    df['Data'] = pd.to_datetime(df['Data'])
                    df['Mês'] = df['Data'].dt.strftime('%Y-%m')
                    
                    resumo_mensal = df.groupby('Mês').agg({
                        'Valor': 'sum',
                        'Descrição': 'count'
                    }).round(2)
                    
                    resumo_mensal.columns = ['Total Mensal', 'Número de Transações']
                    resumo_mensal = resumo_mensal.reset_index()
                    resumo_mensal.to_excel(writer, sheet_name='Resumo Mensal', index=False)
                except:
                    pass
        
        output.seek(0)
        return output
        
    except Exception as e:
        print(f"Erro ao exportar para Excel: {e}")
        return None
    finally:
        session.close()

def exportar_para_csv(usuario_id):
    """Exporta dados para CSV"""
    session = get_session()
    
    try:
        # Buscar transações do usuário
        transacoes = session.query(Transacao).filter_by(usuario_id=usuario_id).all()
        
        if not transacoes:
            return None
        
        # Preparar dados para CSV
        dados = []
        for t in transacoes:
            dados.append({
                'data': t.data.strftime('%Y-%m-%d %H:%M:%S') if t.data else '',
                'descricao': t.descricao or '',
                'valor': str(t.valor).replace('.', ','),
                'tipo': t.tipo or '',
                'banco': t.banco or '',
                'centro_custo': t.centro_custo or '',
                'categoria_ia': t.categoria_ia or '',
                'categoria_manual': t.categoria_manual or '',
                'parcelamento': 'Sim' if t.parcelamento else 'Não',
                'parcela_atual': str(t.parcela_atual) if t.parcela_atual else '',
                'parcela_total': str(t.parcela_total) if t.parcela_total else '',
                'data_vencimento': t.data_vencimento.strftime('%Y-%m-%d') if t.data_vencimento else '',
                'tags': t.tags or ''
            })
        
        # Criar DataFrame
        df = pd.DataFrame(dados)
        
        # Converter para CSV (formato brasileiro)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        csv_data = csv_buffer.getvalue()
        
        return csv_data.encode('utf-8')
        
    except Exception as e:
        print(f"Erro ao exportar para CSV: {e}")
        return None
    finally:
        session.close()

def exportar_relatorio_completo(usuario_id):
    """Exporta relatório completo em JSON"""
    session = get_session()
    
    try:
        # Buscar dados do usuário
        usuario = session.query(Usuario).filter_by(id=usuario_id).first()
        transacoes = session.query(Transacao).filter_by(usuario_id=usuario_id).all()
        categorias = session.query(Categoria).filter_by(usuario_id=usuario_id).all()
        
        # Preparar relatório
        relatorio = {
            'metadata': {
                'usuario': usuario.username if usuario else '',
                'data_exportacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_transacoes': len(transacoes),
                'total_categorias': len(categorias)
            },
            'transacoes': [],
            'categorias': [],
            'resumo': {}
        }
        
        # Adicionar transações
        for t in transacoes:
            relatorio['transacoes'].append({
                'id': t.id,
                'data': t.data.strftime('%Y-%m-%d %H:%M:%S') if t.data else '',
                'descricao': t.descricao,
                'valor': float(t.valor),
                'tipo': t.tipo,
                'banco': t.banco,
                'centro_custo': t.centro_custo,
                'categoria_ia': t.categoria_ia,
                'categoria_manual': t.categoria_manual,
                'parcelamento': t.parcelamento,
                'parcela_atual': t.parcela_atual,
                'parcela_total': t.parcela_total
            })
        
        # Adicionar categorias
        for c in categorias:
            relatorio['categorias'].append({
                'id': c.id,
                'nome': c.nome,
                'tipo': c.tipo,
                'palavras_chave': c.palavras_chave
            })
        
        # Calcular resumo
        if transacoes:
            valores = [float(t.valor) for t in transacoes]
            gastos = sum(v for v in valores if v < 0)
            ganhos = sum(v for v in valores if v > 0)
            
            relatorio['resumo'] = {
                'total_gastos': abs(gastos),
                'total_ganhos': ganhos,
                'saldo': ganhos + gastos,  # gastos é negativo
                'media_mensal': calcular_media_mensal(transacoes)
            }
        
        # Converter para JSON
        json_data = json.dumps(relatorio, indent=2, ensure_ascii=False, default=str)
        
        return json_data.encode('utf-8')
        
    except Exception as e:
        print(f"Erro ao exportar relatório completo: {e}")
        return None
    finally:
        session.close()

def calcular_media_mensal(transacoes):
    """Calcula média mensal de gastos"""
    try:
        # Agrupar por mês
        meses = {}
        for t in transacoes:
            if t.valor < 0:  # Apenas gastos
                if t.data:
                    mes = t.data.strftime('%Y-%m')
                    meses[mes] = meses.get(mes, 0) + abs(t.valor)
        
        if meses:
            return sum(meses.values()) / len(meses)
        return 0.0
    except:
        return 0.0

# Exportar funções
__all__ = [
    'exportar_para_excel',
    'exportar_para_csv',
    'exportar_relatorio_completo',
    'calcular_media_mensal'
]
