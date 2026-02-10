import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== TESTE DE IMPORTAÇÕES ===")

# Testar database
try:
    from database import ConfigSistema, Usuario, Transacao, Categoria
    print("✅ database.py - OK")
except ImportError as e:
    print(f"❌ database.py - ERRO: {e}")

# Testar admin
try:
    from admin import gerenciar_usuarios, gerenciar_categorias, configurar_sistema, backup_dados
    print("✅ admin.py - OK")
except ImportError as e:
    print(f"❌ admin.py - ERRO: {e}")

# Testar auth
try:
    from auth import login_page, check_auth, is_admin
    print("✅ auth.py - OK")
except ImportError as e:
    print(f"❌ auth.py - ERRO: {e}")

print("=== FIM DO TESTE ===")