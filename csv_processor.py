import pandas as pd
import io
import datetime
from database import get_session, Transacao

def _add_months(dt, months):
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, [31,
                       29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return dt.replace(year=year, month=month, day=day)

def _parse_valor_br(valor_str):
    if valor_str is None:
        return 0.0
    s = str(valor_str).strip()
    if not s:
        return 0.0
    # Remover símbolos e espaços
    s = s.replace("R$", "").replace("US$", "").replace(" ", "")
    # Tratar sinal negativo entre parênteses
    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo = True
        s = s[1:-1]
    # Normalizar separadores
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        valor = float(s)
    except:
        valor = 0.0
    return -valor if negativo else valor

def _parse_parcela(valor_parcela):
    if valor_parcela is None:
        return False, None, None
    s = str(valor_parcela).strip()
    if not s or s.lower() in ["unica", "única", "unico", "único"]:
        return False, None, None
    if "/" in s:
        try:
            atual, total = s.split("/", 1)
            return True, int(atual), int(total)
        except:
            return True, None, None
    return True, None, None

def processar_csv(uploaded_file, usuario_id, banco_nome):
    """Processa um arquivo CSV e retorna um DataFrame com as transações"""
    try:
        content = uploaded_file.getvalue()
        # Tentar diferentes encodings
        try:
            df = pd.read_csv(io.BytesIO(content), sep=';', dtype=str, encoding='utf-8')
        except:
            try:
                df = pd.read_csv(io.BytesIO(content), sep=';', dtype=str, encoding='latin-1')
            except:
                df = pd.read_csv(io.BytesIO(content), sep=';', dtype=str, encoding='cp1252')
        
        # Normalizar nomes de colunas
        colunas = {c: c.strip().lower() for c in df.columns}
        df = df.rename(columns=colunas)
        
        # Mapear colunas
        col_data = None
        col_desc = None
        col_valor = None
        col_parcela = None
        col_final_cartao = None
        
        candidatos_data = ['data de compra', 'data', 'data_compra', 'data da compra']
        candidatos_desc = ['descrição', 'descricao', 'histórico', 'historico', 'estabelecimento']
        candidatos_valor = ['valor (em r$)', 'valor', 'valor (r$)', 'valor r$', 'valor (em reais)']
        candidatos_parcela = ['parcela', 'parcelas']
        candidatos_final_cartao = ['final do cartão', 'final do cartao', 'final_cartao', 'cartao', 'cartão']
        
        for c in df.columns:
            if col_data is None and c in candidatos_data:
                col_data = c
            if col_desc is None and c in candidatos_desc:
                col_desc = c
            if col_valor is None and c in candidatos_valor:
                col_valor = c
            if col_parcela is None and c in candidatos_parcela:
                col_parcela = c
            if col_final_cartao is None and c in candidatos_final_cartao:
                col_final_cartao = c
        
        if not col_data or not col_desc or not col_valor:
            raise Exception("CSV não contém colunas necessárias (data, descrição, valor).")
        
        transacoes = []
        for _, row in df.iterrows():
            data_raw = row.get(col_data)
            desc_raw = row.get(col_desc)
            valor_raw = row.get(col_valor)
            
            if not data_raw and not desc_raw and not valor_raw:
                continue
            
            try:
                data_tx = datetime.datetime.strptime(str(data_raw).strip(), '%d/%m/%Y')
            except:
                try:
                    data_tx = datetime.datetime.strptime(str(data_raw).strip(), '%Y-%m-%d')
                except:
                    continue
            
            valor = _parse_valor_br(valor_raw)
            tipo = 'CREDITO' if valor > 0 else 'DEBITO'
            
            descricao = str(desc_raw).strip() if desc_raw is not None else ''
            if descricao and len(descricao) > 198:
                descricao = descricao[:195] + "..."
            
            parcelamento, parcela_atual, parcela_total = _parse_parcela(row.get(col_parcela))

            # Centro de custo
            centro_custo = "Conta Corrente"
            final_cartao = row.get(col_final_cartao) if col_final_cartao else None
            if final_cartao and str(final_cartao).strip() and str(final_cartao).strip() != "-":
                centro_custo = f"Cartao Credito {str(final_cartao).strip()}"
            else:
                desc_lower = descricao.lower()
                if "pix" in desc_lower or "transfer" in desc_lower or "ted" in desc_lower or "doc" in desc_lower:
                    centro_custo = "Transferencia"

            # Ajustar tipo para fatura de cartao: compras positivas sao gasto (DEBITO)
            if centro_custo.startswith("Cartao Credito"):
                if valor > 0:
                    tipo = "DEBITO"
                elif valor < 0:
                    tipo = "CREDITO"

            # Data de competencia: compra + (parcela_atual - 1) meses
            data_compra = data_tx
            data_competencia = data_tx
            if parcelamento and parcela_atual:
                try:
                    data_competencia = _add_months(data_tx, int(parcela_atual) - 1)
                except Exception:
                    data_competencia = data_tx
            
            transacao = {
                'usuario_id': usuario_id,
                'data': data_competencia,
                'data_compra': data_compra,
                'data_competencia': data_competencia,
                'descricao': descricao,
                'valor': valor,
                'tipo': tipo,
                'banco': banco_nome,
                'centro_custo': centro_custo,
                'categoria_ia': None,
                'categoria_manual': None,
                'tags': '',
                'parcelamento': parcelamento,
                'parcela_atual': parcela_atual,
                'parcela_total': parcela_total,
                'data_vencimento': None,
                'processado': False
            }
            transacoes.append(transacao)
        
        if not transacoes:
            return pd.DataFrame()
        
        df_transacoes = pd.DataFrame(transacoes)
        df_transacoes = df_transacoes.drop_duplicates(subset=['data', 'descricao', 'valor'], keep='first')
        df_transacoes = df_transacoes.sort_values('data', ascending=False).reset_index(drop=True)
        
        return df_transacoes
        
    except Exception as e:
        raise Exception(f"Erro ao processar arquivo CSV: {str(e)}")

def verificar_duplicidade(usuario_id, data, descricao, valor):
    """Verifica se uma transação já existe no banco"""
    session = get_session()
    try:
        # Converter data para datetime se for string
        if isinstance(data, str):
            data = datetime.datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
        
        # Buscar transações similares
        transacao = session.query(Transacao).filter(
            Transacao.usuario_id == usuario_id,
            Transacao.data == data,
            Transacao.descricao == descricao,
            Transacao.valor == valor
        ).first()
        
        return transacao is not None
    finally:
        session.close()

def _to_py_datetime(value):
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value

def salvar_transacoes(df_transacoes):
    """Salva transações no banco de dados"""
    session = get_session()
    try:
        if df_transacoes.empty:
            return {'salvas': 0, 'duplicadas': 0, 'total': 0}

        transacoes_salvas = 0
        transacoes_duplicadas = 0

        usuario_id = int(df_transacoes['usuario_id'].iloc[0])
        data_min = _to_py_datetime(df_transacoes['data'].min())
        data_max = _to_py_datetime(df_transacoes['data'].max())

        # Buscar transações existentes no intervalo para evitar N consultas
        existentes = session.query(
            Transacao.data, Transacao.descricao, Transacao.valor
        ).filter(
            Transacao.usuario_id == usuario_id,
            Transacao.data >= data_min,
            Transacao.data <= data_max
        ).all()

        existentes_set = set((d, desc, float(val)) for d, desc, val in existentes)

        novas_transacoes = []
        for _, row in df_transacoes.iterrows():
            data_tx = _to_py_datetime(row['data'])
            chave = (data_tx, row['descricao'], float(row['valor']))

            if chave in existentes_set:
                transacoes_duplicadas += 1
                continue

            transacao_data = row.to_dict()
            transacao_data['data'] = data_tx
            if 'data_vencimento' in transacao_data:
                transacao_data['data_vencimento'] = _to_py_datetime(transacao_data['data_vencimento'])
            # Normalizar campos numéricos opcionais
            if 'parcela_atual' in transacao_data and pd.isna(transacao_data['parcela_atual']):
                transacao_data['parcela_atual'] = None
            if 'parcela_total' in transacao_data and pd.isna(transacao_data['parcela_total']):
                transacao_data['parcela_total'] = None

            novas_transacoes.append(Transacao(**transacao_data))
            existentes_set.add(chave)
            transacoes_salvas += 1

        if novas_transacoes:
            session.add_all(novas_transacoes)
            session.commit()
        
        return {
            'salvas': transacoes_salvas,
            'duplicadas': transacoes_duplicadas,
            'total': len(df_transacoes)
        }
        
    except Exception as e:
        session.rollback()
        raise Exception(f"Erro ao salvar transações: {str(e)}")
    finally:
        session.close()
