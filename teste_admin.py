import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Testando importações...")

try:
    from admin import gerenciar_usuarios, gerenciar_categorias, configurar_sistema, backup_dados
    print("✅ Importação bem-sucedida!")
    print("Funções disponíveis:")
    print(f"  - gerenciar_usuarios: {gerenciar_usuarios}")
    print(f"  - gerenciar_categorias: {gerenciar_categorias}")
    print(f"  - configurar_sistema: {configurar_sistema}")
    print(f"  - backup_dados: {backup_dados}")
except ImportError as e:
    print(f"❌ Erro na importação: {e}")