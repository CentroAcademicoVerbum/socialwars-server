#!/bin/bash
echo "============================================"
echo "  Social Wars Server - Firebase Edition"
echo "============================================"
echo ""

echo "[1/3] Verificando Python..."
python3 --version || { echo "[ERRO] Python3 nao encontrado!"; exit 1; }
echo ""

echo "[2/3] Instalando dependencias..."
pip3 install -r requirements.txt
pip3 install jsonpatch
echo ""

if [ -f "firebase-credentials.json" ]; then
    echo "[OK] firebase-credentials.json encontrado!"
    echo "[INFO] O servidor vai iniciar com Firebase ATIVO."
else
    echo "[AVISO] firebase-credentials.json NAO encontrado!"
    echo "[INFO] O servidor vai iniciar em MODO LOCAL."
fi
echo ""

echo "[3/3] Iniciando servidor..."
echo ""
echo "============================================"
echo "  Acesse no navegador: http://localhost:5055"
echo "============================================"
echo ""

python3 server.py
