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
        # Tentar baixar recursos NLTK (com fallback para Streamlit Cloud)
        self._baixar_recursos_nltk()
        
        # Inicializar componentes de ML
        self.vectorizer = TfidfVectorizer(max_features=500)
        self.classifier = MultinomialNB(alpha=0.1)
        
        # Inicializar stopwords em português (com fallback)
        try:
            from nltk.corpus import stopwords
            self.stop_words = set(stopwords.words('portuguese'))
        except:
            # Fallback para caso não consiga carregar stopwords
            self.stop_words = set(['de', 'da', 'do', 'em', 'para', 'com', 'por'])
        
        # Categorias padrão para treinamento inicial
        self.categorias = {
            'ALIMENTACAO': ['restaurante', 'mercado', 'supermercado', 'padaria', 'lanche', 'ifood', 'comida'],
            'TRANSPORTE': ['uber', 'taxi', 'onibus', 'metro', 'combustivel', 'estacionamento', 'posto', 'gasolina'],
            'MORADIA': ['aluguel', 'condominio', 'luz', 'agua', 'energia', 'internet', 'telefone', 'iptu'],
            'SAUDE': ['farmacia', 'hospital', 'medico', 'plano', 'remedio', 'consulta', 'exame'],
            'EDUCACAO': ['curso', 'faculdade', 'livro', 'material', 'escola', 'universidade', 'mensalidade'],
            'LAZER': ['cinema', 'shopping', 'viagem', 'hotel', 'netflix', 'spotify', 'show'],
            'VESTUARIO': ['roupa', 'calcado', 'loja', 'shopping', 'moda', 'camisa', 'tenis'],
            'SERVICOS': ['conta', 'imposto', 'tarifa', 'assinatura', 'manutencao'],
            'SALARIO': ['salario', 'pagamento', 'rendimento', 'provento'],
            'TRANSFERENCIA': ['transferencia', 'pix', 'ted', 'doc', 'pagamento'],
            'OUTROS': []
        }
        
        # Flag para controle do treinamento
        self.modelo_treinado = False
    
    def _baixar_recursos_nltk(self):
        """Baixa recursos NLTK se necessário (funciona no Streamlit Cloud)"""
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            try:
                nltk.download('stopwords', quiet=True)
            except Exception as e:
                print(f"Aviso: Não foi possível baixar stopwords: {e}")
    
    def preprocess_text(self, text):
        """Pré-processa texto de forma simples e robusta"""
        if not isinstance(text, str):
            return ""
        
        # Converter para minúsculas
        text = text.lower()
        
        # Remover caracteres especiais e números
        text = re.sub(r'[^a-záéíóúãõâêîôûàèìòùç\s]', ' ', text)
        text = re.sub(r'\d+', '', text)
        
        # Tokenizar e limpar
        words = text.split()
        
        # Remover stopwords e palavras muito curtas
        filtered_words = []
        for word in words:
            if word not in self.stop_words and len(word) > 2:
                # Stemming simples: remover sufixos comuns
                if word.endswith('s'):
                    word = word[:-1]
                elif word.endswith('mente'):
                    word = word[:-5]
                filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def treinar_modelo_com_categorias_padrao(self):
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
            print(f"Modelo treinado com {len(dados_treino)} exemplos padrão")
    
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
        """Classifica uma única descrição"""
        try:
            # Se o modelo não foi treinado, treina com categorias padrão
            if not self.modelo_treinado:
                self.treinar_modelo_com_categorias_padrao()
            
            desc_processed = self.preprocess_text(descricao)
            X_vec = self.vectorizer.transform([desc_processed])
            categoria = self.classifier.predict(X_vec)[0]
            return categoria
        except:
            return 'OUTROS'
    
    def classificar_transacoes(self, df_transacoes):
        """Classifica um DataFrame de transações"""
        if df_transacoes.empty:
            return df_transacoes
        
        # Garante que o modelo está treinado
        if not self.modelo_treinado:
            self.treinar_modelo_com_categorias_padrao()
        
        # Classifica cada transação
        categorias = []
        for desc in df_transacoes['descricao']:
            categoria = self.classificar(desc)
            categorias.append(categoria)
        
        df_transacoes['categoria_ia'] = categorias
        return df_transacoes
    
    def carregar_modelo(self, caminho='modelo_classificador.pkl'):
        """Carrega um modelo salvo (opcional)"""
        try:
            if os.path.exists(caminho):
                modelo_data = joblib.load(caminho)
                self.vectorizer = modelo_data['vectorizer']
                self.classifier = modelo_data['classifier']
                self.modelo_treinado = True
                print(f"Modelo carregado de {caminho}")
                return True
        except Exception as e:
            print(f"Não foi possível carregar modelo: {e}")
        return False
    
    def salvar_modelo(self, caminho='modelo_classificador.pkl'):
        """Salva o modelo atual (opcional)"""
        try:
            modelo_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier
            }
            joblib.dump(modelo_data, caminho)
            print(f"Modelo salvo em {caminho}")
            return True
        except Exception as e:
            print(f"Erro ao salvar modelo: {e}")
            return False
