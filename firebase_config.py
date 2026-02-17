"""
Firebase Configuration for Social Warriors Server
===================================================

INSTRUÇÕES DE CONFIGURAÇÃO:

1. Acesse https://console.firebase.google.com
2. Crie um novo projeto (ou use um existente)
3. Ative "Authentication" > "Email/Password" no console
4. Ative "Firestore Database" no console (modo de teste para começar)
5. Vá em "Configurações do Projeto" > "Contas de serviço"
6. Clique em "Gerar nova chave privada" e baixe o arquivo JSON
7. Coloque o arquivo JSON na pasta do projeto e renomeie para "firebase-credentials.json"
   OU cole o caminho completo na variável FIREBASE_CREDENTIALS_PATH abaixo

8. Vá em "Configurações do Projeto" > "Geral" e copie as configurações do Firebase Web App:
   - apiKey, authDomain, projectId, etc.
   - Cole na variável FIREBASE_WEB_CONFIG abaixo
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth

# ============================================================
# CONFIGURAÇÃO - EDITE AQUI
# ============================================================

# Caminho para o arquivo de credenciais do Firebase (Service Account JSON)
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    'FIREBASE_CREDENTIALS_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firebase-credentials.json')
)

# Configuração do Firebase Web SDK (para o frontend)
# Pegue essas informações no Console do Firebase > Configurações do Projeto > Geral > Seus apps
FIREBASE_WEB_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyDEZz66ObrzLT4RSD4JWfJzYmC3tMrAmVY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "socialwarsfan.firebaseapp.com"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID", "socialwarsfan"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "socialwarsfan.firebasestorage.app"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "909624694777"),
    "appId": os.environ.get("FIREBASE_APP_ID", "1:909624694777:web:b755968f0757320a250f28"),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID", "G-SP3TLM6K55"),
}

# ============================================================
# INICIALIZAÇÃO DO FIREBASE ADMIN SDK
# ============================================================

_firebase_app = None
_firestore_db = None
_firebase_initialized = False

def init_firebase():
    """Inicializa o Firebase Admin SDK. Retorna True se bem-sucedido."""
    global _firebase_app, _firestore_db, _firebase_initialized

    if _firebase_initialized:
        return True

    try:
        if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
            print(f" [!] FIREBASE: Arquivo de credenciais não encontrado em: {FIREBASE_CREDENTIALS_PATH}")
            print(f" [!] FIREBASE: O servidor vai rodar em MODO LOCAL (sem Firebase).")
            print(f" [!] FIREBASE: Para ativar, coloque o arquivo 'firebase-credentials.json' na pasta do projeto.")
            return False

        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        _firestore_db = firestore.client()
        _firebase_initialized = True
        print(" [+] FIREBASE: Inicializado com sucesso!")
        return True

    except Exception as e:
        print(f" [!] FIREBASE: Erro ao inicializar: {e}")
        print(f" [!] FIREBASE: O servidor vai rodar em MODO LOCAL (sem Firebase).")
        return False

def get_firestore_db():
    """Retorna a instância do Firestore Database."""
    return _firestore_db

def get_firebase_auth():
    """Retorna o módulo de autenticação do Firebase."""
    return auth

def is_firebase_enabled():
    """Verifica se o Firebase está ativo."""
    return _firebase_initialized

def get_web_config():
    """Retorna a configuração do Firebase Web SDK como JSON string."""
    return json.dumps(FIREBASE_WEB_CONFIG)

def get_web_config_dict():
    """Retorna a configuração do Firebase Web SDK como dicionário."""
    return FIREBASE_WEB_CONFIG
