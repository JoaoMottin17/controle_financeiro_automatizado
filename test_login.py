import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import autenticar_usuario

# Testar autenticação
print("Testando autenticação...")
success, user_data = autenticar_usuario('admin', 'admin123')

if success:
    print(f"✅ Autenticação bem-sucedida!")
    print(f"ID: {user_data['id']}")
    print(f"Username: {user_data['username']}")
    print(f"Nível: {user_data['nivel_acesso']}")
else:
    print("❌ Autenticação falhou")