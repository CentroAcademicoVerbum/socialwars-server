#!/usr/bin/env python3
"""
Script de Migração: Local -> Firebase Firestore
================================================
Execute este script para migrar todas as vilas salvas localmente
(pasta saves/) para o Firebase Firestore.

Uso:
    python3 migrate_to_firebase.py

Requisitos:
    - Arquivo firebase-credentials.json na pasta do projeto
    - Firebase Firestore ativado no console
"""

import os
import sys
import json

# Mudar para o diretório do script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from firebase_config import init_firebase, is_firebase_enabled, get_firestore_db

def main():
    print("=" * 60)
    print("  MIGRAÇÃO: Saves Locais -> Firebase Firestore")
    print("=" * 60)
    print()

    # Inicializar Firebase
    if not init_firebase():
        print("\n[ERRO] Não foi possível inicializar o Firebase.")
        print("Verifique se o arquivo 'firebase-credentials.json' está na pasta do projeto.")
        sys.exit(1)

    db = get_firestore_db()
    saves_dir = os.path.join(".", "saves")

    if not os.path.exists(saves_dir):
        print(f"\n[ERRO] Pasta '{saves_dir}' não encontrada.")
        sys.exit(1)

    files = [f for f in os.listdir(saves_dir) if f.endswith(".save.json")]

    if not files:
        print(f"\n[INFO] Nenhum save encontrado em '{saves_dir}'.")
        sys.exit(0)

    print(f"\nEncontrados {len(files)} save(s) para migrar.\n")

    count = 0
    errors = 0

    for file in files:
        filepath = os.path.join(saves_dir, file)
        try:
            with open(filepath, 'r') as f:
                save = json.load(f)

            if "playerInfo" not in save or "maps" not in save or "privateState" not in save:
                print(f"  [SKIP] {file} - Save inválido")
                continue

            USERID = save["playerInfo"]["pid"]
            name = save["playerInfo"].get("name", "?")

            # Salvar no Firestore (serializado para evitar erro 400 de aninhamento)
            from firebase_sessions import _village_to_firestore
            db.collection("saves").document(USERID).set(_village_to_firestore(save))
            count += 1
            print(f"  [OK] {name} (USERID: {USERID})")

        except Exception as e:
            errors += 1
            print(f"  [ERRO] {file}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  Migração concluída!")
    print(f"  Migrados: {count} | Erros: {errors}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
