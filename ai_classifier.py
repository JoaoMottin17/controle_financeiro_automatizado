import pandas as pd
import numpy as np
import re
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib
import os

class ClassificadorFinanceiro:
    def __init__(self):
        # Garantir que os recursos do NLTK estão baixados
        self._baixar_recursos_nltk()
        
        # Importar depois de garantir recursos
        from nltk.corpus import stopwords
        from nltk.stem import RSLPStemmer
        
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.classifier = MultinomialNB()
        
        try:
            self.stemmer = RSLPStemmer()
            self.stop_words = set(stopwords.words('portuguese'))
        except Exception as e:
            print(f"Aviso: Erro ao inicializar RSLPStemmer: {e}")
            # Fallback - usar stemming simples
            self.stemmer = None
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
            'OUTROS': []  # Adicionei esta linha
        }
    
    def _baixar_recursos_nltk(self):
        """Baixa recursos do NLTK se necessário"""
        try:
            nltk.data.find('corpora/stopwords')
            nltk.data.find('stemmers/rslp')
        except LookupError:
            print("Baixando recursos NLTK...")
            try:
                nltk.download('stopwords', quiet=False)
                nltk.download('rslp', quiet=False)
                print("Recursos NLTK baixados com sucesso!")
            except Exception as e:
                print(f"Erro ao baixar recursos NLTK: {e}")
                # Continua mesmo sem recursos
    
    def preprocess_text(self, text):
        """Pré-processa o texto para classificação"""
        if not isinstance(text, str):
            return ""
        
        # Converter para minúsculas
        text = text.lower()
        
        # Remover caracteres especiais
        text = re.sub(r'[^a-záéíóúãõâêîôûàèìòùç\s]', ' ', text)
        
        # Remover números
        text = re.sub(r'\d+', '', text)
        
        # Tokenizar
        words = text.split()
        
        # Remover stopwords e aplicar stemming (se disponível)
        if self.stemmer and self.stop_words:
            words = [self.stemmer.stem(w) for w in words if w not in self.stop_words]
        else:
            # Fallback: apenas remove palavras muito curtas
            words = [w for w in words if len(w) > 2]
        
        return ' '.join(words)
    
    def treinar_modelo(self, dados_treinamento):
        """Treina o modelo de classificação"""
        try:
            X = [self.preprocess_text(desc) for desc in dados_treinamento['descricao']]
            y = dados_treinamento['categoria']
            
            X_vec = self.vectorizer.fit_transform(X)
            self.classifier.fit(X_vec, y)
            return True
        except Exception as e:
            print(f"Erro ao treinar modelo: {e}")
            return False
    
    def classificar(self, descricao):
        """Classifica uma única descrição"""
        try:
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
        
        # Cria dados de treinamento básicos
        dados_treino = []
        for categoria, palavras in self.categorias.items():
            for palavra in palavras:
                dados_treino.append({
                    'descricao': palavra,
                    'categoria': categoria
                })
        
        # Adiciona transações já classificadas manualmente
        try:
            from database import get_session, Transacao
            session = get_session()
            transacoes_classificadas = session.query(Transacao).filter(
                Transacao.categoria_manual.isnot(None)
            ).limit(100).all()
            
            for t in transacoes_classificadas:
                dados_treino.append({
                    'descricao': t.descricao,
                    'categoria': t.categoria_manual
                })
            session.close()
        except:
            pass
        
        # Treina modelo se houver dados
        df_treino = pd.DataFrame(dados_treino)
        if len(df_treino) > 0:
            self.treinar_modelo(df_treino)
        
        # Classifica novas transações
        categorias = []
        for desc in df_transacoes['descricao']:
            categoria = self.classificar(desc)
            categorias.append(categoria)
        
        df_transacoes['categoria_ia'] = categorias
        return df_transacoes
    
    def salvar_modelo(self, caminho='modelo_classificador.pkl'):
        """Salva o modelo treinado em disco"""
        try:
            modelo_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier
            }
            joblib.dump(modelo_data, caminho)
            return True
        except:
            return False
    
    def carregar_modelo(self, caminho='modelo_classificador.pkl'):
        """Carrega o modelo treinado do disco"""
        try:
            if os.path.exists(caminho):
                modelo_data = joblib.load(caminho)
                self.vectorizer = modelo_data['vectorizer']
                self.classifier = modelo_data['classifier']
                return True
        except:
            pass
        return False
