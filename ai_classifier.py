import pandas as pd
import numpy as np
import re
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib
import os

class ClassificadorFinanceiro:
    def __init__(self):
        # Tentar baixar recursos NLTK
        self._baixar_nltk_se_necessario()
        
        # Inicializar componentes
        self.vectorizer = TfidfVectorizer(max_features=500)
        self.classifier = MultinomialNB(alpha=0.1)
        
        # Inicializar stopwords (com fallback)
        try:
            from nltk.corpus import stopwords
            self.stop_words = set(stopwords.words('portuguese'))
        except:
            self.stop_words = set()
        
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
            'TRANSFERENCIA': ['transferencia', 'pix', 'ted', 'doc'],
            'OUTROS': []
        }
        
        # Flag para saber se o modelo está treinado
        self.modelo_treinado = False
    
    def _baixar_nltk_se_necessario(self):
        """Tenta baixar recursos NLTK se necessário"""
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            try:
                nltk.download('stopwords', quiet=True)
            except:
                print("Não foi possível baixar stopwords do NLTK")
    
    def preprocess_text(self, text):
        """Pré-processa texto de forma simples (sem stemming)"""
        if not isinstance(text, str):
            return ""
        
        # Converter para minúsculas
        text = text.lower()
        
        # Remover caracteres especiais e números
        text = re.sub(r'[^a-záéíóúãõâêîôûàèìòùç\s]', ' ', text)
        text = re.sub(r'\d+', '', text)
        
        # Tokenizar e remover stopwords
        words = text.split()
        words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        return ' '.join(words)
    
    def treinar_modelo(self, dados_treinamento):
        """Treina o modelo com dados de treinamento"""
        try:
            X = [self.preprocess_text(desc) for desc in dados_treinamento['descricao']]
            y = dados_treinamento['categoria']
            
            X_vec = self.vectorizer.fit_transform(X)
            self.classifier.fit(X_vec, y)
            self.modelo_treinado = True
            return True
        except Exception as e:
            print(f"Erro ao treinar modelo: {e}")
            return False
    
    def classificar(self, descricao):
        """Classifica uma descrição"""
        try:
            if not self.modelo_treinado:
                self._treinar_com_categorias_padrao()
            
            desc_processed = self.preprocess_text(descricao)
            X_vec = self.vectorizer.transform([desc_processed])
            categoria = self.classifier.predict(X_vec)[0]
            return categoria
        except:
            return 'OUTROS'
    
    def _treinar_com_categorias_padrao(self):
        """Treina o modelo com as categorias padrão"""
        dados_treino = []
        for categoria, palavras in self.categorias.items():
            for palavra in palavras:
                dados_treino.append({
                    'descricao': palavra,
                    'categoria': categoria
                })
        
        if dados_treino:
            df_treino = pd.DataFrame(dados_treino)
            self.treinar_modelo(df_treino)
    
    def classificar_transacoes(self, df_transacoes):
        """Classifica um DataFrame de transações"""
        if df_transacoes.empty:
            return df_transacoes
        
        # Primeiro treina com categorias padrão
        if not self.modelo_treinado:
            self._treinar_com_categorias_padrao()
        
        # Classifica cada transação
        categorias = []
        for desc in df_transacoes['descricao']:
            categoria = self.classificar(desc)
            categorias.append(categoria)
        
        df_transacoes['categoria_ia'] = categorias
        return df_transacoes
    
    def carregar_modelo(self, caminho='modelo_classificador.pkl'):
        """Carrega um modelo salvo"""
        try:
            if os.path.exists(caminho):
                modelo_data = joblib.load(caminho)
                self.vectorizer = modelo_data['vectorizer']
                self.classifier = modelo_data['classifier']
                self.modelo_treinado = True
                return True
        except:
            pass
        return False
    
    def salvar_modelo(self, caminho='modelo_classificador.pkl'):
        """Salva o modelo atual"""
        try:
            modelo_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier
            }
            joblib.dump(modelo_data, caminho)
            return True
        except:
            return False
