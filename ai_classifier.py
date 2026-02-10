import pandas as pd
import json
import os
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
from database import get_session, CacheClassificacao

class ClassificadorFinanceiro:
    def __init__(self):
        # Categorias padrao do sistema
        self.categorias_padrao = {
            'ALIMENTACAO': ['restaurante', 'mercado', 'supermercado', 'padaria', 'lanche',
                           'ifood', 'delivery', 'comida', 'cafe', 'almoco', 'jantar', 'acougue',
                           'feira', 'hortifruti', 'bakery', 'food', 'starbucks', 'mcdonalds'],
            'TRANSPORTE': ['uber', 'taxi', 'onibus', 'metro', 'combustivel', 'estacionamento',
                          'posto', 'gasolina', 'etanol', 'diesel', 'pedagio', 'uber eats',
                          '99', 'cabify', 'aluguel carro', 'locadora', 'ipva', 'licenciamento'],
            'MORADIA': ['aluguel', 'condominio', 'luz', 'agua', 'energia', 'internet',
                       'telefone', 'gas', 'iptu', 'reforma', 'manutencao', 'limpeza',
                       'eletropaulo', 'sabesp', 'vivo', 'claro', 'oi', 'tim', 'net', 'claro'],
            'SAUDE': ['farmacia', 'hospital', 'medico', 'plano', 'remedio', 'consulta',
                     'dentista', 'laboratorio', 'exame', 'academia', 'fisioterapia', 'psicologo',
                     'drogaria', 'drogasil', 'raia', 'pague menos', 'unimed', 'amil', 'bradesco saude'],
            'EDUCACAO': ['curso', 'faculdade', 'livro', 'material', 'escola', 'universidade',
                        'mensalidade', 'matricula', 'cursinho', 'ingles', 'espanhol', 'professor',
                        'fatec', 'senac', 'senai', 'cultura inglesa', 'wizard'],
            'LAZER': ['cinema', 'shopping', 'viagem', 'hotel', 'netflix', 'spotify', 'streaming',
                     'show', 'teatro', 'parque', 'praia', 'festival', 'disney', 'ingresso',
                     'hbo', 'prime video', 'disney+', 'youtube premium'],
            'VESTUARIO': ['roupa', 'calcado', 'loja', 'shopping', 'moda', 'tenis', 'camisa',
                         'calca', 'vestido', 'sapato', 'sandalia', 'bolsa', 'acessorio',
                         'renner', 'riachuelo', 'c&a', 'marisa', 'zara', 'h&m'],
            'SERVICOS': ['conta', 'imposto', 'tarifa', 'assinatura', 'manutencao', 'conserto',
                        'seguro', 'financiamento', 'taxa', 'juros', 'multa', 'iptu', 'iptu',
                        'irpf', 'darj', 'das', 'gnre'],
            'SALARIO': ['salario', 'pagamento', 'rendimento', 'pro-labore', 'dividendo', 'provento',
                       'beneficio', 'adicional', 'bonificacao', '13o', 'ferias', 'rescisao'],
            'TRANSFERENCIA': ['transferencia', 'pix', 'ted', 'doc', 'pagamento', 'recebimento',
                             'envio', 'deposito', 'saque', 'boleto', 'debito automatico'],
            'INVESTIMENTO': ['aplicacao', 'investimento', 'renda fixa', 'tesouro direto', 'cdb',
                            'lci', 'lca', 'fii', 'acoes', 'bolsa', 'b3', 'corretora', 'xp',
                            'rico', 'btg', 'clear', 'inter', 'nubank', 'modalmais'],
            'OUTROS': []
        }
        self._openai_client = None

    def _get_openai_client(self):
        if not os.getenv("OPENAI_API_KEY"):
            return None
        if OpenAI is None:
            return None
        if self._openai_client is None:
            self._openai_client = OpenAI()
        return self._openai_client

    def obter_palavras_chave_categoria(self, categoria):
        return self.categorias_padrao.get(categoria, [])

    def adicionar_palavra_chave(self, categoria, palavra):
        if categoria in self.categorias_padrao:
            if palavra not in self.categorias_padrao[categoria]:
                self.categorias_padrao[categoria].append(palavra)
                return True
        return False

    def classificar_transacoes_api(self, df_transacoes, batch_size=50, model=None, temperature=0.0):
        if df_transacoes.empty:
            return df_transacoes

        client = self._get_openai_client()
        if client is None:
            raise RuntimeError("OPENAI_API_KEY nao configurada.")

        categorias_validas = list(self.categorias_padrao.keys())
        categorias_validas.sort()

        descricoes = df_transacoes['descricao'].fillna("").tolist()
        categorias_result = [None] * len(descricoes)

        # Cache local por descricao
        session = get_session()
        try:
            existentes = session.query(CacheClassificacao).filter(CacheClassificacao.descricao.in_(descricoes)).all()
            cache_map = {c.descricao: c.categoria for c in existentes}
        finally:
            session.close()

        pendentes = []
        pendentes_idx = []
        for idx, desc in enumerate(descricoes):
            if desc in cache_map:
                categorias_result[idx] = cache_map[desc]
            else:
                pendentes.append(desc)
                pendentes_idx.append(idx)

        model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

        for i in range(0, len(pendentes), batch_size):
            batch = pendentes[i:i+batch_size]
            prompt = (
                "Classifique cada descricao em UMA das categorias a seguir. "
                "Responda SOMENTE com um array JSON de strings, na mesma ordem.\n\n"
                f"Categorias: {categorias_validas}\n\n"
                f"Descricoes: {batch}"
            )
            req = {
                "model": model,
                "input": prompt,
            }
            # Alguns modelos (ex.: gpt-5) não aceitam temperature
            if temperature is not None and not str(model).startswith("gpt-5"):
                req["temperature"] = temperature
            resp = client.responses.create(**req)
            text = getattr(resp, "output_text", None)
            if not text:
                try:
                    text = resp.output[0].content[0].text
                except Exception:
                    text = "[]"
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise ValueError("Resposta nao e lista")
            for j, cat in enumerate(parsed):
                categorias_result[pendentes_idx[i + j]] = cat

            # Salvar no cache
            session = get_session()
            try:
                for j, cat in enumerate(parsed):
                    desc = batch[j]
                    existing = session.query(CacheClassificacao).filter_by(descricao=desc).first()
                    if existing:
                        existing.categoria = cat
                    else:
                        session.add(CacheClassificacao(descricao=desc, categoria=cat))
                session.commit()
            finally:
                session.close()

        for i in range(len(categorias_result)):
            if categorias_result[i] is None:
                categorias_result[i] = 'OUTROS'

        df_transacoes['categoria_ia'] = categorias_result
        df_transacoes['confianca_ia'] = None
        return df_transacoes
