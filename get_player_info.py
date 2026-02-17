from firebase_sessions import session, neighbors, neighbor_session
from engine import timestamp_now, reset_stuff

def get_player_info(USERID):
    # Agora session() vem do firebase_sessions.py e tenta carregar do Firestore
    user_session = session(str(USERID))

    if not user_session:
        print(f" [!] ERRO: Sessão para USERID {USERID} não encontrada em get_player_info.")
        return {"result": "error", "message": "Player not found"}

    ts_now = timestamp_now()

    # Garantir que playerInfo existe
    if "playerInfo" not in user_session:
        print(f" [!] ERRO: playerInfo ausente para USERID {USERID}")
        return {"result": "error", "message": "Invalid player data"}

    user_session["playerInfo"]["last_logged_in"] = ts_now

    # Reset things as some things are taken care of by the server side
    reset_stuff(user_session)

    # player
    player_info = {
        "result": "ok",
        "processed_errors": 0,
        "timestamp": ts_now,
        "playerInfo": user_session["playerInfo"],
        "map": user_session["maps"][0],
        "privateState": user_session["privateState"],
        "neighbors": neighbors(str(USERID))
    }

    return player_info


def get_neighbor_info(userid, map_number):
    _session = neighbor_session(str(userid))

    if not _session:
        print(f"USERID {userid} not found.")
        return {"result": "error", "message": "Neighbor not found"}

    if "playerInfo" not in _session or "maps" not in _session or "privateState" not in _session:
        print(f"USERID {userid} data is incomplete.")
        return {"result": "error", "message": "Incomplete neighbor data"}

    _map_number = map_number if map_number is not None else 0

    # Garantir que o índice do mapa existe
    if _map_number >= len(_session["maps"]):
        _map_number = 0

    neighbor_info = {
        "result": "ok",
        "processed_errors": 0,
        "timestamp": timestamp_now(),
        "playerInfo": _session["playerInfo"],
        "map": _session["maps"][_map_number],
        "privateState": _session["privateState"]
    }
    return neighbor_info
