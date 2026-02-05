import pandas as pd
from ofxparse import OfxParser
from io import StringIO
import datetime
from database import get_session, Transacao

def processar_ofx(uploaded_file, usuario_id, banco_nome):
    try:
        ofx = OfxParser.parse(StringIO(uploaded_file.getvalue().decode('latin-1')))
        
        transacoes = []
        for account in ofx.accounts:
            for transaction in account.statement.transactions:
                transacao = {
                    'usuario_id': usuario_id,
                    'data': transaction.date,
                    'descricao': transaction.memo,
                    'valor': float(transaction.amount),
                    'tipo': 'CREDITO' if transaction.amount > 0 else 'DEBITO',
                    'banco': banco_nome,
                    'categoria_ia': None,
                    'categoria_manual': None,
                    'processado': False
                }
                transacoes.append(transacao)
        
        return pd.DataFrame(transacoes)
    except Exception as e:
        raise Exception(f"Erro ao processar arquivo OFX: {str(e)}")

def salvar_transacoes(df_transacoes):
    session = get_session()
    try:
        for _, row in df_transacoes.iterrows():
            transacao = Transacao(**row.to_dict())
            session.add(transacao)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()