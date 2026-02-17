"""
Social Warriors Server - Com integração Firebase
=================================================
Servidor Flask com autenticação Firebase (email/senha)
e armazenamento de vilas no Firestore.
"""

import os
import logging
import json
import urllib
import requests
import io

if os.name == 'nt':
    os.system("color")
    os.system("title Social Wars Server")
else:
    import sys
    sys.stdout.write("\x1b]2;Social Wars Server\x07")

# ============================================================
# INICIALIZAÇÃO DO FIREBASE
# ============================================================
print(" [+] Loading Firebase...")
from firebase_config import init_firebase, is_firebase_enabled, get_web_config, get_web_config_dict
firebase_ok = init_firebase()
if firebase_ok:
    print(" [+] Firebase ATIVO - Usando autenticação e Firestore")
else:
    print(" [!] Firebase INATIVO - Usando modo local (sem autenticação)")

# ============================================================
# CARREGAMENTO DOS MÓDULOS DO JOGO
# ============================================================
print(" [+] Loading game config...")
from get_game_config import get_game_config

print(" [+] Loading players...")
from get_player_info import get_player_info, get_neighbor_info

# Usar firebase_sessions se Firebase estiver ativo, senão usar sessions original
if is_firebase_enabled():
    from firebase_sessions import (
        load_saves, load_static_villages, load_quests,
        all_saves_userid, all_saves_info, save_info,
        new_village, fb_friends_str, register_user,
        verify_firebase_token, get_userid_from_uid,
        migrate_local_saves_to_firestore
    )
    # Monkey-patch: substituir sessions em todos os módulos que o importam
    import firebase_sessions as active_sessions
    import sys as _sys
    _sys.modules['sessions'] = active_sessions
else:
    from sessions import (
        load_saves, load_static_villages, load_quests,
        all_saves_userid, all_saves_info, save_info,
        new_village, fb_friends_str
    )

load_saves()
print(" [+] Loading static villages...")
load_static_villages()
print(" [+] Loading quests...")
load_quests()

print(" [+] Loading server...")
from flask import Flask, render_template, send_from_directory, request, redirect, session, send_file, jsonify
from flask.debughelpers import attach_enctype_error_multidict
from command import command
from engine import timestamp_now
from version import version_name
from bundle import ASSETS_DIR, STUB_DIR, TEMPLATES_DIR, BASE_DIR
from constants import Quests

host = '0.0.0.0'
port = 5055

app = Flask(__name__)
import os
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only")



print(" [+] Configuring server routes...")

##########
# ROUTES #
##########

__STATIC_ROOT = "/static/socialwars"
__DYNAMIC_ROOT = "/dynamic/menvswomen/srvsexwars"

## PAGES AND RESOURCES

@app.route("/", methods=["GET", "POST", "HEAD"])
def login():
    # Render faz HEAD / pra healthcheck
    if request.method == "HEAD":
        return ("", 200)

    # Log out previous session
    session.pop('USERID', default=None)
    session.pop('GAMEVERSION', default=None)
    session.pop('FIREBASE_UID', default=None)

    if is_firebase_enabled():
        load_saves()

        if request.method == 'POST':
            id_token = request.form.get('id_token')
            if id_token:
                result = verify_firebase_token(id_token)
                if result["success"]:
                    session['USERID'] = result["userid"]
                    session['GAMEVERSION'] = request.form.get('GAMEVERSION', 'Basesec_1.5.4.swf')
                    session['FIREBASE_UID'] = result["uid"]
                    return jsonify({"success": True, "redirect": "/play-ruffle.html"})
                return jsonify({"success": False, "error": result["error"]}), 401

            return jsonify({"success": False, "error": "Token não fornecido."}), 400

        # GET
        return render_template(
            "login_firebase.html",
            version=version_name,
            firebase_config=get_web_config_dict(),  # <- IMPORTANTE (objeto, não string)
            firebase_enabled=True
        )

    # === MODO LOCAL ===
    load_saves()
    if request.method == 'POST':
        session['USERID'] = request.form['USERID']
        session['GAMEVERSION'] = request.form['GAMEVERSION']
        return redirect("/play-ruffle.html")

    saves_info = all_saves_info()
    return render_template("login.html", saves_info=saves_info, version=version_name)


# === ROTAS DE API PARA FIREBASE ===

@app.route("/api/register", methods=['POST'])
def api_register():
    """Registra um novo usuário via Firebase Auth."""
    if not is_firebase_enabled():
        return jsonify({"success": False, "error": "Firebase não está ativo."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Dados inválidos."}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email e senha são obrigatórios."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "error": "A senha deve ter pelo menos 6 caracteres."}), 400

    result = register_user(email, password, display_name or None)
    if result["success"]:
        app.logger.info(f"[REGISTER] Novo usuário: {email}")
        return jsonify(result)
    else:
        return jsonify(result), 400


@app.route("/api/login", methods=['POST'])
def api_login():
    """Login via Firebase Token (verificação server-side)."""
    if not is_firebase_enabled():
        return jsonify({"success": False, "error": "Firebase não está ativo."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Dados inválidos."}), 400

    id_token = data.get("id_token")
    game_version = data.get("game_version", "Basesec_1.5.4.swf")

    if not id_token:
        return jsonify({"success": False, "error": "Token não fornecido."}), 400

    result = verify_firebase_token(id_token)
    if result["success"]:
        session['USERID'] = result["userid"]
        session['GAMEVERSION'] = game_version
        session['FIREBASE_UID'] = result["uid"]
        app.logger.info(f"[LOGIN-FIREBASE] UID: {result['uid']}, Email: {result['email']}")
        return jsonify({"success": True, "redirect": "/play-ruffle.html", "userid": result["userid"]})
    else:
        return jsonify({"success": False, "error": result["error"]}), 401


@app.route("/api/migrate", methods=['POST'])
def api_migrate():
    """Migra vilas locais para o Firestore."""
    if not is_firebase_enabled():
        return jsonify({"success": False, "error": "Firebase não está ativo."}), 503
    try:
        migrate_local_saves_to_firestore()
        return jsonify({"success": True, "message": "Migração concluída."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# === ROTAS DO JOGO (mantidas iguais) ===

@app.route("/play.html")
def play():
    if 'USERID' not in session:
        return redirect("/")
    if 'GAMEVERSION' not in session:
        return redirect("/")
    if session['USERID'] not in all_saves_userid():
        return redirect("/")

    USERID = session['USERID']
    GAMEVERSION = session['GAMEVERSION']
    print("[PLAY] USERID:", USERID)
    print("[PLAY] GAMEVERSION:", GAMEVERSION)
    return render_template("play.html", save_info=save_info(USERID), serverTime=timestamp_now(), friendsInfo=fb_friends_str(USERID), version=version_name, GAMEVERSION=GAMEVERSION, SERVERIP=host, SERVERPORT=port)


@app.route("/new.html")
def new():
    session['USERID'] = new_village()
    session['GAMEVERSION'] = "Basesec_1.5.4.swf"
    return redirect("play-ruffle.html")


@app.route("/crossdomain.xml")
def crossdomain():
    return send_from_directory(STUB_DIR, "crossdomain.xml")


@app.route("/img/<path:path>")
def images(path):
    return send_from_directory(TEMPLATES_DIR + "/img", path)


@app.route("/avatars/<path:path>")
def avatars(path):
    return send_from_directory(TEMPLATES_DIR + "/avatars", path)


@app.route("/css/<path:path>")
def css(path):
    return send_from_directory(TEMPLATES_DIR + "/css", path)


# Ruffle self-hosted files
RUFFLE_DIR = os.path.join(BASE_DIR, "ruffle")

@app.route("/ruffle/<path:path>")
def ruffle_files(path):
    response = send_from_directory(RUFFLE_DIR, path)
    if path.endswith('.wasm'):
        response.headers['Content-Type'] = 'application/wasm'
    return response


@app.route("/play-ruffle.html")
def play_ruffle():
    if 'USERID' not in session:
        return redirect("/")
    if 'GAMEVERSION' not in session:
        return redirect("/")
    if session['USERID'] not in all_saves_userid():
        return redirect("/")
    USERID = session['USERID']
    GAMEVERSION = session['GAMEVERSION']
    app.logger.info(f"[PLAY-RUFFLE] USERID: {USERID}")
    app.logger.info(f"[PLAY-RUFFLE] GAMEVERSION: {GAMEVERSION}")
    return render_template("play-ruffle.html", save_info=save_info(USERID), serverTime=timestamp_now(), friendsInfo=fb_friends_str(USERID), version=version_name, GAMEVERSION=GAMEVERSION, SERVERIP=host, SERVERPORT=port)


## GAME STATIC

@app.route(__STATIC_ROOT + "/<path:path>")
def static_assets_loader(path):
    # LITE-WEIGHT BUILD: ASSETS FROM GITHUB
    if False:
        cdn = "https://raw.githubusercontent.com/AcidCaos/socialwarriors/main/assets/"
        try:
            r = requests.get(cdn + path)
        except requests.exceptions:
            return ""
        m = io.BytesIO(r.content)
        m.seek(0)
        return send_file(m, download_name=path.split("/")[-1:][0])
    # OFFLINE BUILD
    return send_from_directory(ASSETS_DIR, path)


## GAME DYNAMIC

@app.route(__DYNAMIC_ROOT + "/track_game_status.php", methods=['POST'])
def track_game_status_response():
    status = request.values['status']
    installId = request.values['installId']
    user_id = request.values['user_id']
    app.logger.info(f"[STATUS] USERID {user_id}: {status}")
    return ("", 200)


@app.route(__DYNAMIC_ROOT + "/get_game_config.php")
def get_game_config_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']
    app.logger.info(f"[CONFIG] USERID {USERID}.")
    return get_game_config()


@app.route(__DYNAMIC_ROOT + "/get_player_info.php", methods=['POST'])
def get_player_info_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']

    user = request.values['user'] if 'user' in request.values else None
    client_id = int(request.values['client_id']) if 'client_id' in request.values else None
    map = int(request.values['map']) if 'map' in request.values else None

    # Current Player
    if user is None:
        app.logger.info(f"[PLAYER INFO] USERID {USERID}.")
        return (get_player_info(USERID), 200)
    # General Mike
    elif user in ["100000030", "100000031"]:
        app.logger.info(f"[VISIT] USERID {USERID} visiting General Mike ({user}).")
        return (get_neighbor_info("100000030", map), 200)
    # Quest Maps
    elif user.startswith("100000"):
        app.logger.info(f"[QUEST] USERID {USERID} loading {Quests.QUEST[user] if user in Quests.QUEST else '?'}({user}).")
        return (get_neighbor_info(user, map), 200)
    # Static Neighbours
    else:
        app.logger.info(f"[VISIT] USERID {USERID} visiting user: {user}.")
        return (get_neighbor_info(user, map), 200)


@app.route(__DYNAMIC_ROOT + "/sync_error_track.php", methods=['POST'])
def sync_error_track_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']
    return ("", 200)


@app.route("/null")
def flash_sync_error_response():
    sp_ref_cat = request.values['sp_ref_cat']

    if sp_ref_cat == "flash_sync_error":
        reason = "reload On Sync Error"
    elif sp_ref_cat == "flash_reload_quest":
        reason = "reload On End Quest"
    elif sp_ref_cat == "flash_reload_attack":
        reason = "reload On End Attack"

    app.logger.warning(f"flash_sync_error {reason}. -- {request.values}")
    return redirect("/play-ruffle.html")


@app.route(__DYNAMIC_ROOT + "/command.php", methods=['POST'])
def command_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']

    data_str = request.values['data']
    data_hash = data_str[:64]
    assert data_str[64] == ';'
    data_payload = data_str[65:]
    data = json.loads(data_payload)

    command(USERID, data)

    return ({"result": "success"}, 200)


# Used by Player's World and Alliance buttons
@app.route(__DYNAMIC_ROOT + "/alliance/", methods=['POST'])
def alliance():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']
    method = request.values['method']

    response = {}
    return (response, 200)


########
# MAIN #
########

print(" [+] Running server...")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5055)))



    import logging
    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.propagate = False
        app.run(host=host, port=port, debug=False)
