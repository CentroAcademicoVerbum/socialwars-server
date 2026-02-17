import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth

# ============================================================
# CONFIGURAÇÃO
# ============================================================

# 1) Preferência: credenciais vindo do Render (ENV) como JSON inteiro
FIREBASE_CREDENTIALS_JSON = (
    os.environ.get("FIREBASE_CREDENTIALS_JSON")
    or os.environ.get("FIREBASE_CREDENTIALS")
    or ""
).strip()

# 2) Fallback: caminho do arquivo local (dev)
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "FIREBASE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase-credentials.json")
)

# Configuração do Firebase Web SDK (frontend)
FIREBASE_WEB_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", ""),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID", ""),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
    "appId": os.environ.get("FIREBASE_APP_ID", ""),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID", ""),
}

_firebase_app = None
_firestore_db = None
_firebase_initialized = False


def init_firebase() -> bool:
    """
    Inicializa o Firebase Admin SDK.
    Retorna True se bem-sucedido.
    """
    global _firebase_app, _firestore_db, _firebase_initialized

    if _firebase_initialized:
        return True

    try:
        cred = None
        project_id = None

        # --- Preferir ENV JSON (Render) ---
        if FIREBASE_CREDENTIALS_JSON:
            try:
                cred_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
            except json.JSONDecodeError as e:
                print(f" [!] FIREBASE: FIREBASE_CREDENTIALS_JSON inválido (JSON mal formatado): {e}")
                print(" [!] FIREBASE: Rodando em MODO LOCAL (sem Firebase).")
                return False

            project_id = cred_dict.get("project_id")
            cred = credentials.Certificate(cred_dict)

        # --- Fallback arquivo local ---
        elif os.path.exists(FIREBASE_CREDENTIALS_PATH):
            try:
                with open(FIREBASE_CREDENTIALS_PATH, "r", encoding="utf-8") as f:
                    file_dict = json.load(f)
                project_id = file_dict.get("project_id")
            except Exception:
                project_id = None

            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)

        else:
            print(" [!] FIREBASE: Credenciais não encontradas (ENV nem arquivo).")
            print(" [!] FIREBASE: Rodando em MODO LOCAL (sem Firebase).")
            return False

        # Ajuda alguns ambientes (não é obrigatório, mas facilita)
        if project_id and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

        # Evita erro de "app already exists" em alguns cenários
        if not firebase_admin._apps:
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            _firebase_app = firebase_admin.get_app()

        _firestore_db = firestore.client()
        _firebase_initialized = True

        print(" [+] FIREBASE: Inicializado com sucesso!")
        if project_id:
            print(f" [+] FIREBASE: project_id = {project_id}")
        return True

    except Exception as e:
        print(f" [!] FIREBASE: Erro ao inicializar: {e}")
        print(" [!] FIREBASE: Rodando em MODO LOCAL (sem Firebase).")
        return False


def get_firestore_db():
    return _firestore_db


def get_firebase_auth():
    return auth


def is_firebase_enabled() -> bool:
    return _firebase_initialized


def get_web_config() -> str:
    return json.dumps(FIREBASE_WEB_CONFIG)


def get_web_config_dict() -> dict:
    return FIREBASE_WEB_CONFIG
