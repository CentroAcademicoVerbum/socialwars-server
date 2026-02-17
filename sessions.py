import json
import os
import copy
import uuid
import random
from flask import session  # (não usado aqui, mas mantive igual seu)
from version import version_code
from engine import timestamp_now
from version import migrate_loaded_save
from constants import Quests
from bundle import VILLAGES_DIR, QUESTS_DIR, SAVES_DIR

# === Firebase fallback (novo) ===
try:
    from firebase_sessions import load_village_from_firestore
except Exception:
    load_village_from_firestore = None


__villages = {}  # ALL static neighbors
__quests = {}    # ALL static quests
__saves = {}     # ALL saved villages

__initial_village = json.load(open(os.path.join(VILLAGES_DIR, "initial.json")))

# Load saved villages

def load_saves():
    global __saves

    # Empty in memory
    __saves = {}

    # Saves dir check
    if not os.path.exists(SAVES_DIR):
        try:
            print(f"Creating '{SAVES_DIR}' folder...")
            os.mkdir(SAVES_DIR)
        except:
            print(f"Could not create '{SAVES_DIR}' folder.")
            exit(1)

    if not os.path.isdir(SAVES_DIR):
        print(f"'{SAVES_DIR}' is not a folder... Move the file somewhere else.")
        exit(1)

    # Saves in /saves
    for file in os.listdir(SAVES_DIR):
        print(f" * Loading SAVE: village at {file}... ", end='')
        try:
            save = json.load(open(os.path.join(SAVES_DIR, file), encoding="utf-8"))
        except json.decoder.JSONDecodeError:
            print("Corrupted JSON.")
            continue
        except Exception as e:
            print(f"Error: {e}")
            continue

        if not is_valid_village(save):
            print("Invalid Save")
            continue

        USERID = str(save["playerInfo"]["pid"])
        print("PLAYER USERID:", USERID)
        __saves[USERID] = save

        modified = migrate_loaded_save(save)  # check save version for migration
        if modified:
            save_session(USERID)


def load_static_villages():
    global __villages

    # Empty in memory
    __villages = {}

    # Static neighbors in /villages
    for file in os.listdir(VILLAGES_DIR):
        if file == "initial.json" or not file.endswith(".json"):
            continue
        print(f" * Loading STATIC NEIGHBOUR: village at {file}... ", end='')
        village = json.load(open(os.path.join(VILLAGES_DIR, file), encoding="utf-8"))
        if not is_valid_village(village):
            print("Invalid neighbour")
            continue
        USERID = str(village["playerInfo"]["pid"])
        print("STATIC USERID:", USERID)
        __villages[USERID] = village


def load_quests():
    global __quests

    # Empty in memory
    __quests = {}

    # Static quests in /villages/quest
    for file in os.listdir(QUESTS_DIR):
        print(f" * Loading ", end='')
        village = json.load(open(os.path.join(QUESTS_DIR, file), encoding="utf-8"))
        if not is_valid_village(village):
            print("Invalid Quest")
            continue
        QUESTID = str(village["playerInfo"]["pid"])
        assert file.split(".")[0] == QUESTID
        quest_name = Quests.QUEST[QUESTID] if QUESTID in Quests.QUEST else "?"
        print(quest_name)
        __quests[QUESTID] = village


# New village

def new_village() -> str:
    # Generate USERID
    USERID: str = str(uuid.uuid4())
    assert USERID not in all_userid()

    # Copy init
    village = copy.deepcopy(__initial_village)

    # Custom values
    village["version"] = None  # Do not set version, migrate_loaded_save() does it
    village["playerInfo"]["pid"] = USERID
    village["maps"][0]["timestamp"] = timestamp_now()

    # Make sure that the game will initialize targets by calling darts_reset
    village["privateState"]["timeStampDartsReset"] = 0

    # Migrate it if needed
    migrate_loaded_save(village)

    # Memory saves
    __saves[USERID] = village

    # Generate save file
    save_session(USERID)
    print("Done.")
    return USERID


# Access functions

def all_saves_userid() -> list:
    "Returns a list of the USERID of every saved village."
    return list(__saves.keys())


def all_userid() -> list:
    "Returns a list of the USERID of every village."
    return list(__villages.keys()) + list(__saves.keys()) + list(__quests.keys())


def save_info(USERID: str) -> dict:
    save = __saves[USERID]
    default_map = save["playerInfo"]["default_map"]
    empire_name = str(save["playerInfo"]["name"])
    xp = save["maps"][default_map]["xp"]
    level = save["maps"][default_map]["level"]
    return {"userid": USERID, "name": empire_name, "xp": xp, "level": level}


def all_saves_info() -> list:
    saves_info = []
    for userid in __saves:
        saves_info.append(save_info(userid))
    return list(saves_info)


# ✅ CORRIGIDO: session() agora tenta Firestore quando não achar no cache
def session(USERID: str) -> dict:
    assert isinstance(USERID, str)

    # 1) cache local
    if USERID in __saves:
        return __saves[USERID]

    # 2) fallback Firestore (coleção "saves")
    if load_village_from_firestore:
        vill = load_village_from_firestore(USERID)
        if vill and is_valid_village(vill):
            __saves[USERID] = vill
            return vill

    return None


def neighbor_session(USERID: str) -> dict:
    assert isinstance(USERID, str)
    if USERID in __saves:
        return __saves[USERID]
    if USERID in __quests:
        return __quests[USERID]
    if USERID in __villages:
        return __villages[USERID]


def fb_friends_str(USERID: str) -> list:
    friends = []
    # static villages
    for key in __villages:
        vill = __villages[key]
        if vill["playerInfo"]["pid"] == "100000030" or vill["playerInfo"]["pid"] == "100000031":  # general Mike
            continue
        frie = {"uid": vill["playerInfo"]["pid"], "pic_square": vill["playerInfo"]["pic"]}
        friends += [frie]

    # other players
    for key in __saves:
        vill = __saves[key]
        if vill["playerInfo"]["pid"] == USERID:
            continue
        frie = {"uid": vill["playerInfo"]["pid"], "pic_square": vill["playerInfo"]["pic"]}
        friends += [frie]

    return friends


def neighbors(USERID: str):
    neighbors = []

    # static villages
    for key in __villages:
        vill = __villages[key]
        if vill["playerInfo"]["pid"] == "100000030" or vill["playerInfo"]["pid"] == "100000031":  # general Mike
            continue
        neigh = json.loads(json.dumps(vill["playerInfo"]))
        neigh["xp"] = vill["maps"][0]["xp"]
        neigh["level"] = vill["maps"][0]["level"]
        neigh["gold"] = vill["maps"][0]["gold"]
        neigh["wood"] = vill["maps"][0]["wood"]
        neigh["oil"] = vill["maps"][0]["oil"]
        neigh["steel"] = vill["maps"][0]["steel"]
        neighbors += [neigh]

    # other players
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
        neighbors += [neigh]

    return neighbors


# Check for valid village

def is_valid_village(save: dict):
    if "playerInfo" not in save or "maps" not in save or "privateState" not in save:
        return False

    if not isinstance(save["maps"], list) or not isinstance(save["privateState"], dict) or not isinstance(save["playerInfo"], dict):
        return False

    for m in save["maps"]:
        if "oil" not in m or "steel" not in m:
            return False
        if "stone" in m or "food" in m:
            return False
        if "items" not in m:
            return False
        if type(m["items"]) != dict:
            return False

    return True


# Persistency

def backup_session(USERID: str):
    return


def save_session(USERID: str):
    file = f"{USERID}.save.json"
    print(f" * Saving village at {file}... ", end='')
    village = session(USERID)
    if not village:
        print("Skipped (no session).")
        return
    with open(os.path.join(SAVES_DIR, file), 'w', encoding="utf-8") as f:
        json.dump(village, f, indent=4, ensure_ascii=False)
    print("Done.")
