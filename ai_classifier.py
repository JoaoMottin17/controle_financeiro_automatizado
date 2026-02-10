import pandas as pd
import numpy as np
import re
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer
import joblib
import os

# Baixar recursos do NLTK se necessário
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('rslp', quiet=True)

class ClassificadorFinanceiro:
    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=1000, min_df=2, max_df=0.8)),
            ('clf', MultinomialNB(alpha=0.1))
        ])
        
        self.stemmer = RSLPStemmer()
        self.stop_words = set(stopwords.words('portuguese'))
        
        # Categorias padrão do sistema
        self.categorias_padrao = {
            'ALIMENTACAO': ['restaurante', 'mercado', 'supermercado', 'padaria', 'lanche', 
                           'ifood', 'delivery', 'comida', 'café', 'almoço', 'jantar', 'açougue',
                           'feira', 'hortifruti', 'bakery', 'food', 'starbucks', 'mcdonalds'],
            'TRANSPORTE': ['uber', 'taxi', 'ônibus', 'metro', 'combustivel', 'estacionamento', 
                          'posto', 'gasolina', 'etanol', 'diesel', 'pedágio', 'uber eats',
                          '99', 'cabify', 'aluguel carro', 'locadora', 'ipva', 'licenciamento'],
            'MORADIA': ['aluguel', 'condominio', 'luz', 'agua', 'energia', 'internet', 
                       'telefone', 'gás', 'iptu', 'reforma', 'manutenção', 'limpeza',
                       'eletropaulo', 'sabesp', 'vivo', 'claro', 'oi', 'tim', 'net', 'claro'],
            'SAUDE': ['farmacia', 'hospital', 'médico', 'plano', 'remédio', 'consulta', 
                     'dentista', 'laboratório', 'exame', 'academia', 'fisioterapia', 'psicólogo',
                     'drogaria', 'drogasil', 'raia', 'pague menos', 'unimed', 'amil', 'bradesco saúde'],
            'EDUCACAO': ['curso', 'faculdade', 'livro', 'material', 'escola', 'universidade', 
                        'mensalidade', 'matrícula', 'cursinho', 'inglês', 'espanhol', 'professor',
                        'fatec', 'senac', 'senai', 'cultura inglesa', 'wizard'],
            'LAZER': ['cinema', 'shopping', 'viagem', 'hotel', 'netflix', 'spotify', 'streaming',
                     'show', 'teatro', 'parque', 'praia', 'festival', 'disney', 'ingresso',
                     'hbo', 'prime video', 'disney+', 'youtube premium'],
            'VESTUARIO': ['roupa', 'calçado', 'loja', 'shopping', 'moda', 'tenis', 'camisa',
                         'calça', 'vestido', 'sapato', 'sandália', 'bolsa', 'acessório',
                         'renner', 'riachuelo', 'c&a', 'marisa', 'zara', 'h&m'],
            'SERVICOS': ['conta', 'imposto', 'tarifa', 'assinatura', 'manutenção', 'conserto',
                        'seguro', 'financiamento', 'taxa', 'juros', 'multa', 'iptu', 'iptu',
                        'irpf', 'darj', 'das', 'gnre'],
            'SALARIO': ['salário', 'pagamento', 'rendimento', 'pró-labore', 'dividendo', 'provento',
                       'benefício', 'adicional', 'bonificação', '13º', 'férias', 'rescisão'],
            'TRANSFERENCIA': ['transferência', 'pix', 'ted', 'doc', 'pagamento', 'recebimento',
                             'envio', 'depósito', 'saque', 'boleto', 'débito automático'],
            'INVESTIMENTO': ['aplicação', 'investimento', 'renda fixa', 'tesouro direto', 'cdb',
                            'lci', 'lca', 'fii', 'ações', 'bolsa', 'b3', 'corretora', 'xp',
                            'rico', 'btg', 'clear', 'inter', 'nubank', 'modalmais'],
            'OUTROS': []  # Categoria para tudo que não se encaixa
        }
        
        self.modelo_treinado = False
    
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
        
        # Remover stopwords e aplicar stemming
        words = [self.stemmer.stem(w) for w in words if w not in self.stop_words]
        
        return ' '.join(words)
    
    def criar_dados_treinamento(self):
        """Cria dados de treinamento baseados nas categorias padrão"""
        textos = []
        categorias = []
        
        for categoria, palavras in self.categorias_padrao.items():
            for palavra in palavras:
                textos.append(self.preprocess_text(palavra))
                categorias.append(categoria)
        
        return pd.DataFrame({
            'texto': textos,
            'categoria': categorias
        })
    
    def treinar_modelo(self, dados_adicionais=None):
        """Treina o modelo de classificação"""
        try:
            # Criar dados de treinamento padrão
            df_treino = self.criar_dados_treinamento()
            
            # Adicionar dados adicionais se fornecidos
            if dados_adicionais is not None and not dados_adicionais.empty:
                dados_adicionais['texto'] = dados_adicionais['descricao'].apply(self.preprocess_text)
                df_treino = pd.concat([df_treino, dados_adicionais[['texto', 'categoria']]])
            
            # Remover duplicatas
            df_treino = df_treino.drop_duplicates()
            
            # Treinar modelo
            X = df_treino['texto']
            y = df_treino['categoria']
            
            self.pipeline.fit(X, y)
            self.modelo_treinado = True
            
            print(f"✅ Modelo treinado com {len(df_treino)} exemplos")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao treinar modelo: {e}")
            return False
    
    def classificar_descricao(self, descricao):
        """Classifica uma única descrição"""
        if not self.modelo_treinado:
            self.treinar_modelo()
        
        try:
            descricao_processada = self.preprocess_text(descricao)
            categoria = self.pipeline.predict([descricao_processada])[0]
            return categoria
        except:
            return 'OUTROS'
    
    def classificar_transacoes(self, df_transacoes):
        """Classifica um DataFrame de transações"""
        if df_transacoes.empty:
            return df_transacoes
        
        # Verificar se o modelo precisa ser treinado
        if not self.modelo_treinado:
            self.treinar_modelo()
        
        # Classificar cada transação
        categorias = []
        confiancas = []
        
        for descricao in df_transacoes['descricao']:
            categoria = self.classificar_descricao(descricao)
            categorias.append(categoria)
            
            # Calcular confiança (simplificado)
            try:
                descricao_processada = self.preprocess_text(descricao)
                proba = self.pipeline.predict_proba([descricao_processada])[0]
                confianca = np.max(proba)
                confiancas.append(float(confianca))
            except:
                confiancas.append(0.5)
        
        df_transacoes['categoria_ia'] = categorias
        df_transacoes['confianca_ia'] = confiancas
        
        return df_transacoes
    
    def salvar_modelo(self, caminho='modelo_classificador.pkl'):
        """Salva o modelo treinado em disco"""
        if self.modelo_treinado:
            joblib.dump(self.pipeline, caminho)
            print(f"✅ Modelo salvo em {caminho}")
            return True
        return False
    
    def carregar_modelo(self, caminho='modelo_classificador.pkl'):
        """Carrega o modelo treinado do disco"""
        try:
            if os.path.exists(caminho):
                self.pipeline = joblib.load(caminho)
                self.modelo_treinado = True
                print(f"✅ Modelo carregado de {caminho}")
                return True
        except:
            pass
        return False
    
    def obter_palavras_chave_categoria(self, categoria):
        """Retorna palavras-chave para uma categoria específica"""
        return self.categorias_padrao.get(categoria, [])
    
    def adicionar_palavra_chave(self, categoria, palavra):
        """Adiciona uma nova palavra-chave a uma categoria"""
        if categoria in self.categorias_padrao:
            if palavra not in self.categorias_padrao[categoria]:
                self.categorias_padrao[categoria].append(palavra)
                # Retreinar o modelo
                self.treinar_modelo()
                return True
        return False