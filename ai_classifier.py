import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

nltk.download('stopwords')
nltk.download('rslp')

class ClassificadorFinanceiro:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.classifier = MultinomialNB()
        self.stemmer = RSLPStemmer()
        self.stop_words = set(stopwords.words('portuguese'))
        
        # Categorias padrão
        self.categorias = {
            'ALIMENTACAO': ['restaurante', 'mercado', 'supermercado', 'padaria', 'lanche', 'ifood'],
            'TRANSPORTE': ['uber', 'taxi', 'onibus', 'metro', 'combustivel', 'estacionamento', 'posto'],
            'MORADIA': ['aluguel', 'condominio', 'luz', 'agua', 'energia', 'internet', 'telefone'],
            'SAUDE': ['farmacia', 'hospital', 'medico', 'plano', 'remedio', 'consulta'],
            'EDUCACAO': ['curso', 'faculdade', 'livro', 'material', 'escola', 'universidade'],
            'LAZER': ['cinema', 'shopping', 'viagem', 'hotel', 'netflix', 'spotify'],
            'VESTUARIO': ['roupa', 'calcado', 'loja', 'shopping', 'moda'],
            'SERVICOS': ['conta', 'imposto', 'tarifa', 'assinatura'],
            'SALARIO': ['salario', 'pagamento', 'rendimento'],
            'TRANSFERENCIA': ['transferencia', 'pix', 'ted', 'doc']
        }
    
    def preprocess_text(self, text):
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r'[^a-záéíóúãõâêîôûàèìòùç\s]', '', text)
        words = text.split()
        words = [self.stemmer.stem(w) for w in words if w not in self.stop_words]
        return ' '.join(words)
    
    def treinar_modelo(self, dados_treinamento):
        X = [self.preprocess_text(desc) for desc in dados_treinamento['descricao']]
        y = dados_treinamento['categoria']
        
        X_vec = self.vectorizer.fit_transform(X)
        self.classifier.fit(X_vec, y)
    
    def classificar(self, descricao):
        desc_processed = self.preprocess_text(descricao)
        X_vec = self.vectorizer.transform([desc_processed])
        categoria = self.classifier.predict(X_vec)[0]
        return categoria
    
    def classificar_transacoes(self, df_transacoes):
        # Cria dados de treinamento básicos
        dados_treino = []
        for categoria, palavras in self.categorias.items():
            for palavra in palavras:
                dados_treino.append({
                    'descricao': palavra,
                    'categoria': categoria
                })
        
        # Adiciona transações já classificadas manualmente
        from database import get_session, Transacao
        session = get_session()
        try:
            transacoes_classificadas = session.query(Transacao).filter(
                Transacao.categoria_manual.isnot(None)
            ).limit(100).all()
            
            for t in transacoes_classificadas:
                dados_treino.append({
                    'descricao': t.descricao,
                    'categoria': t.categoria_manual
                })
        finally:
            session.close()
        
        # Treina modelo
        df_treino = pd.DataFrame(dados_treino)
        if len(df_treino) > 0:
            self.treinar_modelo(df_treino)
        
        # Classifica novas transações
        categorias = []
        for desc in df_transacoes['descricao']:
            try:
                categoria = self.classificar(desc)
            except:
                categoria = 'OUTROS'
            categorias.append(categoria)
        
        df_transacoes['categoria_ia'] = categorias
        return df_transacoes