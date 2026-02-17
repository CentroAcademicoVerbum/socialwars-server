"""
Firebase Sessions - Gerenciamento de vilas usando Firestore
============================================================
Substitui o armazenamento local em arquivos JSON pelo Firebase Firestore.
Mantém compatibilidade total com a interface do sessions.py original.

NOTA: O Firestore NÃO suporta arrays aninhados (arrays dentro de arrays).
As vilas do Social Wars usam essa estrutura (maps[].items = [item_id, x, y, ts, orient, [], {}, player]).
Solução: salvar os dados complexos (maps, privateState) como JSON string no Firestore,
e deserializar ao carregar.
"""

import json
import copy
import uuid
import os

from firebase_config import get_firestore_db, get_firebase_auth, is_firebase_enabled
from version import version_code
from engine import timestamp_now
from version import migrate_loaded_save
from constants import Quests
from bundle import VILLAGES_DIR, QUESTS_DIR

# ============================================================
# COLEÇÕES DO FIRESTORE
# ============================================================
USERS_COLLECTION = "users"          # Dados de autenticação/perfil
SAVES_COLLECTION = "saves"          # Vilas dos jogadores

# ============================================================
# CACHE EM MEMÓRIA (para performance)
# ============================================================
__villages = {}   # Vilas estáticas (NPCs) - carregadas do disco
__quests = {}     # Quests estáticas - carregadas do disco
__saves = {}      # Cache das vilas dos jogadores (sincronizado com Firestore)

__initial_village = json.load(open(os.path.join(VILLAGES_DIR, "initial.json")))


# ============================================================
# SERIALIZAÇÃO PARA O FIRESTORE
# ============================================================
# O Firestore não aceita arrays dentro de arrays.
# Solução: salvar maps e privateState como JSON strings.

def _village_to_firestore(village: dict) -> dict:
    """Converte uma vila para formato compatível com o Firestore."""
    return {
        "playerInfo": village["playerInfo"],  # dict simples, OK para Firestore
        "maps_json": json.dumps(village["maps"]),  # serializar como string
        "privateState_json": json.dumps(village["privateState"]),  # serializar como string
        "version": village.get("version", "0.02a"),
    }


def _firestore_to_village(doc_data: dict) -> dict:
    """Converte dados do Firestore de volta para o formato de vila."""
    return {
        "playerInfo": doc_data["playerInfo"],
        "maps": json.loads(doc_data["maps_json"]),
        "privateState": json.loads(doc_data["privateState_json"]),
        "version": doc_data.get("version", "0.02a"),
    }


# ============================================================
# AUTENTICAÇÃO COM FIREBASE
# ============================================================

def register_user(email: str, password: str, display_name: str = None) -> dict:
    """
    Registra um novo usuário no Firebase Auth e cria uma vila para ele.
    Retorna: {"success": True, "uid": "...", "userid": "..."} ou {"success": False, "error": "..."}
    """
    if not is_firebase_enabled():
        return {"success": False, "error": "Firebase não está configurado."}

    try:
        auth = get_firebase_auth()
        # Criar usuário no Firebase Auth
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=display_name or email.split("@")[0]
        )
        uid = user_record.uid

        # Criar uma nova vila para o usuário
        userid = _create_village_for_user(uid, display_name or email.split("@")[0])

        # Salvar dados do usuário no Firestore
        db = get_firestore_db()
        db.collection(USERS_COLLECTION).document(uid).set({
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "userid": userid,
            "created_at": timestamp_now(),
            "last_login": timestamp_now()
        })

        return {"success": True, "uid": uid, "userid": userid}

    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg or "already exists" in error_msg.lower():
            return {"success": False, "error": "Este email já está cadastrado."}
        if "WEAK_PASSWORD" in error_msg or "6 characters" in error_msg:
            return {"success": False, "error": "A senha deve ter pelo menos 6 caracteres."}
        if "INVALID_EMAIL" in error_msg:
            return {"success": False, "error": "Email inválido."}
        return {"success": False, "error": f"Erro ao registrar: {error_msg}"}


def verify_firebase_token(id_token: str) -> dict:
    """
    Verifica um token de ID do Firebase (enviado pelo frontend).
    Retorna: {"success": True, "uid": "...", "email": "..."} ou {"success": False, "error": "..."}
    """
    if not is_firebase_enabled():
        return {"success": False, "error": "Firebase não está configurado."}

    try:
        auth = get_firebase_auth()
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')

        # Atualizar último login
        db = get_firestore_db()
        user_doc = db.collection(USERS_COLLECTION).document(uid).get()

        if user_doc.exists:
            db.collection(USERS_COLLECTION).document(uid).update({
                "last_login": timestamp_now()
            })
            user_data = user_doc.to_dict()
            userid = user_data.get("userid")

            # Garantir que a vila está carregada na memória
            if userid:
                _load_single_save(userid)

        else:
            # Usuário existe no Auth mas não no Firestore (primeira vez)
            display_name = decoded_token.get('name', email.split("@")[0])
            userid = _create_village_for_user(uid, display_name)
            db.collection(USERS_COLLECTION).document(uid).set({
                "email": email,
                "display_name": display_name,
                "userid": userid,
                "created_at": timestamp_now(),
                "last_login": timestamp_now()
            })

        return {"success": True, "uid": uid, "email": email, "userid": userid}

    except Exception as e:
        return {"success": False, "error": f"Token inválido: {str(e)}"}


def get_userid_from_uid(uid: str) -> str:
    """Retorna o USERID (ID da vila) a partir do UID do Firebase Auth."""
    if not is_firebase_enabled():
        return None

    try:
        db = get_firestore_db()
        user_doc = db.collection(USERS_COLLECTION).document(uid).get()
        if user_doc.exists:
            return user_doc.to_dict().get("userid")
        return None
    except:
        return None


# ============================================================
# CRIAÇÃO DE VILAS
# ============================================================

def _create_village_for_user(uid: str, display_name: str) -> str:
    """Cria uma nova vila no Firestore para um usuário. Retorna o USERID."""
    USERID = str(uuid.uuid4())

    # Copiar vila inicial
    village = copy.deepcopy(__initial_village)
    village["version"] = None
    village["playerInfo"]["pid"] = USERID
    village["playerInfo"]["name"] = display_name
    village["maps"][0]["timestamp"] = timestamp_now()
    village["privateState"]["timeStampDartsReset"] = 0

    # Migrar se necessário
    migrate_loaded_save(village)

    # Salvar no Firestore (serializado)
    db = get_firestore_db()
    db.collection(SAVES_COLLECTION).document(USERID).set(_village_to_firestore(village))

    # Cache em memória
    __saves[USERID] = village

    print(f" [+] FIREBASE: Nova vila criada para {display_name} (USERID: {USERID})")
    return USERID


def new_village() -> str:
    """Cria uma nova vila (compatibilidade com o sistema antigo)."""
    USERID = str(uuid.uuid4())
    assert USERID not in all_userid()

    village = copy.deepcopy(__initial_village)
    village["version"] = None
    village["playerInfo"]["pid"] = USERID
    village["maps"][0]["timestamp"] = timestamp_now()
    village["privateState"]["timeStampDartsReset"] = 0

    migrate_loaded_save(village)

    # Salvar no Firestore (serializado)
    if is_firebase_enabled():
        db = get_firestore_db()
        db.collection(SAVES_COLLECTION).document(USERID).set(_village_to_firestore(village))

    # Cache em memória
    __saves[USERID] = village

    print(f" [+] Nova vila criada (USERID: {USERID})")
    return USERID


# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================

def _load_single_save(userid: str):
    """Carrega uma única vila do Firestore para a memória."""
    if not is_firebase_enabled():
        return
    try:
        db = get_firestore_db()
        doc = db.collection(SAVES_COLLECTION).document(userid).get()
        if doc.exists:
            doc_data = doc.to_dict()
            # Verificar se é formato novo (serializado) ou antigo
            if "maps_json" in doc_data:
                village = _firestore_to_village(doc_data)
            else:
                village = doc_data  # formato antigo
            if is_valid_village(village):
                __saves[str(userid)] = village
                print(f" * FIREBASE: Vila {userid} carregada com sucesso.")
            else:
                print(f" [!] FIREBASE: Vila {userid} encontrada mas é inválida.")
        else:
            print(f" [!] FIREBASE: Vila {userid} não encontrada no Firestore.")
    except Exception as e:
        print(f" [!] FIREBASE: Erro ao carregar vila {userid}: {e}")


def load_saves():
    """Carrega todas as vilas salvas do Firestore (ou do disco se Firebase não estiver ativo)."""
    global __saves
    __saves = {}

    if is_firebase_enabled():
        try:
            db = get_firestore_db()
            docs = db.collection(SAVES_COLLECTION).stream()
            for doc in docs:
                doc_data = doc.to_dict()
                # Verificar se é formato novo (serializado) ou antigo
                if "maps_json" in doc_data:
                    save = _firestore_to_village(doc_data)
                else:
                    save = doc_data
                if not is_valid_village(save):
                    print(f" * FIREBASE: Vila inválida ignorada: {doc.id}")
                    continue
                USERID = save["playerInfo"]["pid"]
                __saves[str(USERID)] = save
                modified = migrate_loaded_save(save)
                if modified:
                    save_session(USERID)
            print(f" [+] FIREBASE: {len(__saves)} vila(s) carregada(s) do Firestore.")
        except Exception as e:
            print(f" [!] FIREBASE: Erro ao carregar vilas: {e}")
            print(f" [!] FIREBASE: Tentando carregar do disco...")
            _load_saves_from_disk()
    else:
        _load_saves_from_disk()


def _load_saves_from_disk():
    """Fallback: carrega vilas do disco (pasta saves/)."""
    global __saves
    from bundle import SAVES_DIR

    if not os.path.exists(SAVES_DIR):
        try:
            os.mkdir(SAVES_DIR)
        except:
            print(f"Could not create '{SAVES_DIR}' folder.")
            return

    for file in os.listdir(SAVES_DIR):
        try:
            save = json.load(open(os.path.join(SAVES_DIR, file)))
        except json.decoder.JSONDecodeError:
            print(f"Corrupted JSON: {file}")
            continue
        if not is_valid_village(save):
            continue
        USERID = save["playerInfo"]["pid"]
        __saves[str(USERID)] = save
        modified = migrate_loaded_save(save)
        if modified:
            save_session(USERID)


def load_static_villages():
    """Carrega vilas estáticas (NPCs) do disco."""
    global __villages
    __villages = {}

    for file in os.listdir(VILLAGES_DIR):
        if file == "initial.json" or not file.endswith(".json"):
            continue
        village = json.load(open(os.path.join(VILLAGES_DIR, file)))
        if not is_valid_village(village):
            continue
        USERID = village["playerInfo"]["pid"]
        __villages[str(USERID)] = village


def load_quests():
    """Carrega quests estáticas do disco."""
    global __quests
    __quests = {}

    for file in os.listdir(QUESTS_DIR):
        village = json.load(open(os.path.join(QUESTS_DIR, file)))
        if not is_valid_village(village):
            continue
        QUESTID = village["playerInfo"]["pid"]
        __quests[str(QUESTID)] = village


# ============================================================
# FUNÇÕES DE ACESSO (compatíveis com sessions.py original)
# ============================================================

def all_saves_userid() -> list:
    """Retorna lista de USERIDs de todas as vilas salvas."""
    return list(__saves.keys())


def all_userid() -> list:
    """Retorna lista de USERIDs de todas as vilas."""
    return list(__villages.keys()) + list(__saves.keys()) + list(__quests.keys())


def save_info(USERID: str) -> dict:
    """Retorna informações resumidas de uma vila."""
    if USERID not in __saves:
        # Tentar carregar do Firestore se não estiver no cache
        _load_single_save(USERID)
    
    if USERID not in __saves:
        return None
        
    save = __saves[USERID]
    default_map = save["playerInfo"]["default_map"]
    empire_name = str(save["playerInfo"]["name"])
    xp = save["maps"][default_map]["xp"]
    level = save["maps"][default_map]["level"]
    return {"userid": USERID, "name": empire_name, "xp": xp, "level": level}


def all_saves_info() -> list:
    """Retorna informações de todas as vilas salvas."""
    saves_info = []
    for userid in __saves:
        info = save_info(userid)
        if info:
            saves_info.append(info)
    return list(saves_info)


def session(USERID: str) -> dict:
    """Retorna os dados completos de uma vila."""
    assert isinstance(USERID, str)
    if USERID not in __saves:
        _load_single_save(USERID)
    return __saves[USERID] if USERID in __saves else None


def neighbor_session(USERID: str) -> dict:
    """Retorna os dados de uma vila vizinha."""
    assert isinstance(USERID, str)
    if USERID in __saves:
        return __saves[USERID]
    if USERID in __quests:
        return __quests[USERID]
    if USERID in __villages:
        return __villages[USERID]
    
    # Tentar carregar do Firestore se for um save
    _load_single_save(USERID)
    return __saves.get(USERID)


def fb_friends_str(USERID: str) -> list:
    """Retorna lista de amigos (vizinhos) para o jogo."""
    friends = []
    for key in __villages:
        vill = __villages[key]
        if vill["playerInfo"]["pid"] in ["100000030", "100000031"]:
            continue
        frie = {
            "uid": vill["playerInfo"]["pid"],
            "pic_square": vill["playerInfo"]["pic"]
        }
        friends.append(frie)
    for key in __saves:
        vill = __saves[key]
        if vill["playerInfo"]["pid"] == USERID:
            continue
        frie = {
            "uid": vill["playerInfo"]["pid"],
            "pic_square": vill["playerInfo"]["pic"]
        }
        friends.append(frie)
    return friends


def neighbors(USERID: str):
    """Retorna lista de vizinhos para o jogo."""
    neighbor_list = []
    for key in __villages:
        vill = __villages[key]
        if vill["playerInfo"]["pid"] in ["100000030", "100000031"]:
            continue
        neigh = json.loads(json.dumps(vill["playerInfo"]))
        neigh["xp"] = vill["maps"][0]["xp"]
        neigh["level"] = vill["maps"][0]["level"]
        neigh["gold"] = vill["maps"][0]["gold"]
        neigh["wood"] = vill["maps"][0]["wood"]
        neigh["oil"] = vill["maps"][0]["oil"]
        neigh["steel"] = vill["maps"][0]["steel"]
        neighbor_list.append(neigh)
    for key in __saves:
        vill = __saves[key]
        if vill["playerInfo"]["pid"] == USERID:
            continue
        neigh = json.loads(json.dumps(vill["playerInfo"]))
        neigh["xp"] = vill["maps"][0]["xp"]
        neigh["level"] = vill["maps"][0]["level"]
        neigh["gold"] = vill["maps"][0]["gold"]
        neigh["wood"] = vill["maps"][0]["wood"]
        neigh["oil"] = vill["maps"][0]["oil"]
        neigh["steel"] = vill["maps"][0]["steel"]
        neighbor_list.append(neigh)
    return neighbor_list


# ============================================================
# VALIDAÇÃO
# ============================================================

def is_valid_village(save: dict):
    """Verifica se uma vila é válida."""
    if not save or "playerInfo" not in save or "maps" not in save or "privateState" not in save:
        return False
    return True


# ============================================================
# PERSISTÊNCIA
# ============================================================

def backup_session(USERID: str):
    """Backup de uma sessão (TODO)."""
    return


def save_session(USERID: str):
    """Salva uma vila no Firestore (serializada) e opcionalmente no disco como backup."""
    village = session(USERID)
    if not village:
        print(f" [!] Erro: Vila {USERID} não encontrada na memória.")
        return

    if is_firebase_enabled():
        try:
            db = get_firestore_db()
            db.collection(SAVES_COLLECTION).document(USERID).set(_village_to_firestore(village))
            print(f" * FIREBASE: Vila {USERID} salva no Firestore.")
        except Exception as e:
            print(f" [!] FIREBASE: Erro ao salvar vila {USERID}: {e}")
            _save_session_to_disk(USERID, village)
    else:
        _save_session_to_disk(USERID, village)


def _save_session_to_disk(USERID: str, village: dict):
    """Fallback: salva vila no disco."""
    from bundle import SAVES_DIR
    file = f"{USERID}.save.json"
    with open(os.path.join(SAVES_DIR, file), 'w') as f:
        json.dump(village, f, indent=4)


# ============================================================
# MIGRAÇÃO: Importar vilas locais para o Firestore
# ============================================================

def migrate_local_saves_to_firestore():
    """Migra todas as vilas salvas localmente para o Firestore."""
    if not is_firebase_enabled():
        return

    from bundle import SAVES_DIR
    if not os.path.exists(SAVES_DIR):
        return

    db = get_firestore_db()
    count = 0

    for file in os.listdir(SAVES_DIR):
        if not file.endswith(".save.json"):
            continue
        try:
            save = json.load(open(os.path.join(SAVES_DIR, file)))
            if not is_valid_village(save):
                continue
            USERID = save["playerInfo"]["pid"]
            db.collection(SAVES_COLLECTION).document(USERID).set(_village_to_firestore(save))
            count += 1
        except Exception as e:
            print(f" [!] Erro ao migrar {file}: {e}")

    print(f" [+] Migração concluída: {count} vila(s) migrada(s) para o Firestore.")
